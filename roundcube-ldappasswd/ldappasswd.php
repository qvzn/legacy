<?php
/*-
 * Copyright (c) 2014, Dima Dorfman
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

/**
 * Password change driver using the OpenLDAP ldappasswd(1) utility
 *
 * Advantages of this method:
 *  - No extra configuration if OpenLDAP/ldappasswd are already configured
 *  - Indifferent to password storage (attribute) and hashing details
 *  - Future-proof: supports everything ldappasswd(1) can do now, and later
 *  - TLS/SSF verification is done by OpenLDAP according to system settings
 *  - Uses PASSMOD extended operation; no need to retrieve full user record
 *
 * Disadvantages:
 *  - ldappasswd(1) must be installed and configured on the local system
 *
 **************************************************************************
 ***                        COMPATIBILITY NOTICE                        ***
 ***          This implementation REQUIRES /dev/fd/N for N>2            ***
 ***         On BSD variants you may need to mount fdescfs(4)           ***
 **************************************************************************
 *
 * Unlike, e.g., GnuPG, ldappasswd(1) does not support passing a numeric fd
 * from which to read a password. Since writing the password to a temporary
 * file or passing on the command line is unacceptable, /dev/fd is the only
 * secure method if we want a non-interactive option
 */
class rcube_ldappasswd_password
{
    public function save($currpass, $newpass)
    {
        if (!($cmd = self::expanded_cmd()))
            return PASSWORD_ERROR;
        $fds = array(0 => array('pipe', 'r'));
        if ($cppipe = strpos($cmd, '%currpasspipe') !== false) {
            $fds[3] = array('pipe', 'r');
            $cmd = str_replace('%currpasspipe', '/dev/fd/3', $cmd);
        }
        $proc = proc_open($cmd, $fds, $pipes);
        if (!is_resource($proc))
            return PASSWORD_ERROR;
        foreach($pipes as $pipe)
            stream_set_blocking($pipe, 0);
        fwrite($pipes[0], $newpass);
        if ($cppipe)
            fwrite($pipes[3], $currpass);
        foreach($pipes as $pipe)
            fclose($pipe);
        if (($status = proc_close($proc)) == 0)
            return PASSWORD_SUCCESS;
        else {
            rcube::raise_error(array(
                'code' => 600,
                'type' => 'php',
                'file' => __FILE__, 'line' => __LINE__,
                'message' => "ldappasswd exec failed, status=$status; $cmd"
                ), true, false);
            return PASSWORD_ERROR;
        }
    }

    private function expanded_cmd()
    {
        $rcmail = rcmail::get_instance();
        return self::substitute_vars(
            $rcmail->config->get('password_ldappasswd_cmd'));
    }

    /**
     * [Duplicated from ldap.php]
     * XXX: Should this be called directly from ldap.php somehow? Our
     * XXX: config comments promise compatibility and local macros are
     * XXX: already implemented in another pass
     * Substitute %login, %name, %domain, %dc in $str
     * See plugin config for details
     */
    static function substitute_vars($str)
    {
        $str = str_replace('%login', $_SESSION['username'], $str);
        $str = str_replace('%l', $_SESSION['username'], $str);

        $parts = explode('@', $_SESSION['username']);

        if (count($parts) == 2) {
            $dc = 'dc='.strtr($parts[1], array('.' => ',dc=')); // hierarchal domain string

            $str = str_replace('%name', $parts[0], $str);
            $str = str_replace('%n', $parts[0], $str);
            $str = str_replace('%dc', $dc, $str);
            $str = str_replace('%domain', $parts[1], $str);
            $str = str_replace('%d', $parts[1], $str);
        }

        return $str;
    }
}
