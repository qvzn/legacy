;;; arinrest.el --- Interactive ARIN RESTful editing
;;; Dima Dorfman, March 2013. Created from:

;;; restclient.el --- An interactive HTTP client for Emacs

;; Public domain.

;; Author: Pavel Kurnosov <pashky@gmail.com>
;; Maintainer: Pavel Kurnosov <pashky@gmail.com>
;; Created: 01 Apr 2012
;; Keywords: http

;; This file is not part of GNU Emacs.
;; This file is public domain software. Do what you want.

(require 'url)
(require 'json-reformat)

(defcustom arinrest-same-buffer-response t
  "Re-use same buffer for responses or create a new one each time")

(defcustom arinrest-same-buffer-response-name "*ARIN Response*"
  "Name for response buffer")

(defcustom arinrest-apikey nil
  "ARIN API key (automatically appended to URL if set)")

(defvar arinrest-within-call nil)

; The following disables the interactive request for user name and
; password should an API call encounter a permission-denied response.
; This API is meant to be usable without constant asking for username
; and password.
(defadvice url-http-handle-authentication (around arinrest-fix)
  (if arinrest-within-call
	  (setq success t)
	ad-do-it)
  (setq arinrest-within-call nil))
(ad-activate 'url-http-handle-authentication)

(defadvice url-cache-extract (around arinrest-fix-2)
  (if arinrest-within-call
	  (setq success t)
	ad-do-it)
  (setq arinrest-within-call nil))
(ad-activate 'url-cache-extract)

(defun arinrest-restore-header-variables ()
  (url-set-mime-charset-string)
  (setq url-mime-language-string nil)
  (setq url-mime-encoding-string nil)
  (setq url-mime-accept-string nil)
  (setq url-personal-mail-address nil))

(defun arinrest-http-do (method url headers entity raw)
  "Send ARGS to URL as a POST request."
  (let ((url-request-method method)
        (url-request-extra-headers '())
        (url-request-data entity))

    (arinrest-restore-header-variables)
    (when arinrest-apikey
      (setq url (format "%s?apikey=%s" url arinrest-apikey)))
    
    (dolist (header headers)
      (let* ((mapped (assoc-string (downcase (car header))
                                   '(("from" . url-personal-mail-address)
                                     ("accept-encoding" . url-mime-encoding-string)
                                     ("accept-charset" . url-mime-charset-string)
                                     ("accept-language" . url-mime-language-string)
                                     ("accept" . url-mime-accept-string)))))
        
        (if mapped
            (set (cdr mapped) (cdr header))
          (setq url-request-extra-headers (cons header url-request-extra-headers)))
        ))

	(setq arinrest-within-call t)
	(url-retrieve url 'arinrest-http-handle-response
				  (list (if arinrest-same-buffer-response
							arinrest-same-buffer-response-name
						  (format "*HTTP %s %s*" method url)) raw))))


(defun arinrest-prettify-response ()
  (save-excursion
	(let ((start (point)) (guessed-mode) (arin-hack))
	  (while (not (looking-at "^\\s-*$"))
	        (when (looking-at "^Server: Apache-Coyote/1.1$")
		  (setq arin-hack t))
		(when (looking-at "^Content-[Tt]ype: \\([^; \n]+\\).*$")
		  (setq guessed-mode
				(cdr (assoc-string
					  (buffer-substring-no-properties (match-beginning 1) (match-end 1))
					  '(("text/xml" . xml-mode)
						("application/xml" . xml-mode)
						("application/json" . js-mode)
						("image/png" . image-mode)
						("image/jpeg" . image-mode)
						("image/gif" . image-mode)
						("text/html" . html-mode))))))
		(forward-line))
	  (when (and (not guessed-mode) arin-hack)
	    (setq guessed-mode 'xml-mode))
	  (let ((headers (buffer-substring-no-properties start (point))))
		(forward-line)
		(when guessed-mode
		  (delete-region start (point))
		  (unless (eq guessed-mode 'image-mode)
			(apply guessed-mode '())
			(font-lock-fontify-buffer))

		  (cond
		   ((eq guessed-mode 'xml-mode)
			(goto-char (point-min))
			(while (search-forward-regexp "\>[ \\t]*\<" nil t)
			  (backward-char) (insert "\n"))
			(indent-region (point-min) (point-max)))

		   ((eq guessed-mode 'image-mode)
			(let* ((img (buffer-string)))
			  (delete-region (point-min) (point-max))
			  (fundamental-mode)
			  (insert-image (create-image img nil t))

			  ))

		   ((eq guessed-mode 'js-mode)
			(json-reformat-region (point-min) (point-max))))

		  (goto-char (point-max))
		  (let ((hstart (point)))
			(insert "\n" headers)
			(unless (eq guessed-mode 'image-mode)
			  (comment-region hstart (point))
			  (indent-region hstart (point)))))))))

(defun arinrest-http-handle-response (status bufname raw)
  "Switch to the buffer returned by `url-retreive'.
    The buffer contains the raw HTTP response sent by the server."
  (arinrest-restore-header-variables)
  (if arinrest-same-buffer-response
      (if (get-buffer arinrest-same-buffer-response-name)
	  (kill-buffer arinrest-same-buffer-response-name)))
  (arinrest-decode-response (current-buffer) bufname)
  (unless raw
    (arinrest-prettify-response))
  (buffer-enable-undo))

(defun arinrest-decode-response (raw-http-response-buffer target-buffer-name)
  "Decode the HTTP response using the charset (encoding) specified in the
   Content-Type header. If no charset is specified, default to UTF-8."
  (let* ((charset-regexp "Content-Type.*charset=\\([-A-Za-z0-9]+\\)")
         (image? (save-excursion
                   (search-forward-regexp "Content-Type.*[Ii]mage" nil t)))
	 (encoding (if (save-excursion
			 (search-forward-regexp charset-regexp nil t))
		       (intern (downcase (match-string 1)))
		     'utf-8)))
    (if image?
        ;; Dont' attempt to decode. Instead, just switch to the raw HTTP response buffer and
        ;; rename it to target-buffer-name.
        (progn
          (switch-to-buffer-other-window raw-http-response-buffer)
          (rename-buffer target-buffer-name))
      ;; Else, switch to the new, empty buffer that will contain the decoded HTTP
      ;; response. Set its encoding, copy the content from the unencoded
      ;; HTTP response buffer and decode.
      (let ((decoded-http-response-buffer (get-buffer-create
                                           (generate-new-buffer-name target-buffer-name))))
        (switch-to-buffer-other-window decoded-http-response-buffer)
        (setq buffer-file-coding-system encoding)
        (save-excursion
          (insert-buffer-substring raw-http-response-buffer))
        (kill-buffer raw-http-response-buffer)
        (condition-case nil
            (decode-coding-region (point-min) (point-max) encoding)
          (error
           (message (concat "Error when trying to decode http response with encoding: "
                            (symbol-name encoding)))))))))

(defconst arinrest-method-url-regexp
  "^\\(GET\\|POST\\|DELETE\\|PUT\\|HEAD\\|OPTIONS\\|PATCH\\) \\(.*\\)$")

(defconst arinrest-header-regexp
  "^\\([^ :]+\\): \\(.*\\)$")

(defun arinrest-current-min ()
  (save-excursion
	(beginning-of-line)
	(if (looking-at "^#")
		(if (re-search-forward "^[^#]" (point-max) t)
			(point-at-bol))
	  (if (re-search-backward "^#" (point-min) t)
		  (point-at-bol 2)
		(point-min)))))

(defun arinrest-current-max ()
  (save-excursion
	(if (re-search-forward "^#" (point-max) t)
		(point-at-bol)
	  (point-max))))


;;;###autoload
(defun arinrest-http-send-current (&optional raw)
  (interactive)
  (goto-char (arinrest-current-min))
  (save-excursion
	(when (re-search-forward arinrest-method-url-regexp (point-max) t)
	  (let ((method (buffer-substring-no-properties (match-beginning 1) (match-end 1)))
			(url (buffer-substring-no-properties (match-beginning 2) (match-end 2)))
			(headers '()))
			(forward-line)
			(while (re-search-forward arinrest-header-regexp (point-at-eol) t)
			  (setq headers (cons (cons (buffer-substring-no-properties (match-beginning 1) (match-end 1))
										(buffer-substring-no-properties (match-beginning 2) (match-end 2)))
								  headers))
			  (forward-line))
			(when (looking-at "^\\s-*$")
			  (forward-line))
			(let ((entity (buffer-substring (point) (arinrest-current-max))))
			  (message "HTTP %s %s Headers:[%s] Body:[%s]" method url headers entity)
			  (arinrest-http-do method url headers entity raw))))))

;;;###autoload
(defun arinrest-http-send-current-raw ()
  (interactive)
  (arinrest-http-send-current t))

(setq arinrest-mode-keywords
	  (list (list arinrest-method-url-regexp '(1 font-lock-keyword-face) '(2 font-lock-function-name-face))
			(list arinrest-header-regexp '(1 font-lock-variable-name-face) '(2 font-lock-string-face))

			))

(defvar arinrest-mode-syntax-table
  (let ((table (make-syntax-table)))
	(modify-syntax-entry ?\# "<" table)
	(modify-syntax-entry ?\n ">#" table)
	table))

;;;###autoload
(define-derived-mode arinrest-mode fundamental-mode "ARIN REST Client"

  (local-set-key "\C-c\C-c" 'arinrest-http-send-current)
  (local-set-key "\C-c\C-r" 'arinrest-http-send-current-raw)
  (set (make-local-variable 'comment-start) "# ")
  (set (make-local-variable 'comment-start-skip) "#\\W*")
  (set (make-local-variable 'comment-column) 48)

  (set (make-local-variable 'font-lock-defaults) '(arinrest-mode-keywords)))


(provide 'arinrest)
;;; arinrest.el ends here
