(defun system-is-mac ()
  (interactive)
  (string-equal system-type "darwin"))

(menu-bar-mode 1)

(setq emacs-d (expand-file-name "~/.local.d/etc/spacemacs"))
(setq tmp-d (expand-file-name "~/.local.d/var/tmp"))

(require 'undo-tree)
(require 'goto-chg)

;; Disable smartparens for most pairs, my editing style doesn't play well with it
(eval-after-load 'smartparens
  '(progn
     (sp-pair "(" nil :actions :rem)
     (sp-pair "[" nil :actions :rem)
     (sp-pair "{" nil :actions :rem)
     (sp-pair "'" nil :actions :rem)
     (sp-pair "`" nil :actions :rem)
     (sp-pair "\"" nil :actions :rem)))
;;(eval-after-load 'smartparens
;;  '(progn
;;     (sp-local-pair 'inferior-python-mode "(" nil :unless nil)
;;     (sp-local-pair 'inferior-python-mode "[" nil :unless nil)
;;     (sp-local-pair 'inferior-python-mode "'" nil :unless nil)
;;     (sp-local-pair 'inferior-python-mode "\"" nil :unless nil)))

;; visual-line-mode wraps lines prettyly!
(global-visual-line-mode 1)

; ---------------------------------------------------------------------------- ;
; Remember last cursor position
(setq save-place-file (format "%s/%s" emacs-d "save-place"))
(require 'saveplace)
(setq-default save-place t)

; -- relocate other files so we don't clutter $HOME
(setq diary-file (format "%s/%s" emacs-d "diary"))

; ---------------------------------------------------------------------------- ;
; -- default and initial frame size
(setq initial-frame-alist '((width . 85) (height . 55)))
(add-to-list 'initial-frame-alist '(top . 1))
(setq default-frame-alist '((width . 85) (height . 55)))
(add-to-list 'default-frame-alist '(top . 1))
(setq default-frame-alist (copy-alist initial-frame-alist))

;; Starts the Emacs server
;; synctex will not work without it.
;; (server-start)

; Set the fill column
(setq default-fill-column 80)
(setq auto-fill-mode 1)

; switch between buffers
(global-set-key '[C-tab] 'bs-cycle-next)
(global-set-key [S-tab] 'bs-cycle-previous)

; inhibit startup message
(setq inhibit-startup-message t)
(add-hook 'emacs-startup-hook
          (lambda () (delete-other-windows)) t)

; Case insensitive search
(setq case-fold-search t)

; disable upcase and downcase warning
(put 'upcase-region 'disabled nil)
(put 'downcase-region 'disabled nil)

; line numbers
(setq line-number-mode t)
(line-number-mode 1)
(column-number-mode 1)
(global-linum-mode 1)

; Improve scrolling
(setq scroll-step 1)

; Title at top of frame
(setq frame-title-format ' buffer-file-name )

; I don't know what this does
(setq enable-recursive-minibuffers t)

; Autosaved files in one place
(setq delete-auto-save-files nil)
;;(setq auto-save-list-file-prefix (format "%s/%s/" tmp-d ".saves/"))
(defvar autosave-dir (format "%s/%s/" tmp-d "saves.d"))
(defun auto-save-file-name-p (filename)
  (string-match "^#.*#$" (file-name-nondirectory filename)))
(defun make-auto-save-file-name ()
  (concat autosave-dir
   (if buffer-file-name
      (concat "#" (file-name-nondirectory buffer-file-name) "#")
    (expand-file-name
     (concat "#%" (buffer-name) "#")))))

; Backup files (ie foo~) in one place too.
(setq vc-make-backup-files t)
(defvar backup-dir (format "%s/%s" tmp-d "backups.d/"))
(setq backup-directory-alist (list (cons "." backup-dir)))
(setq backup-by-copying t)
(setq delete-old-versions t
      kept-new-versions 2
      kept-old-versions 1
      version-control t
      )

; delete \b at line ends before saving a file
(add-hook 'write-file-hooks 'delete-trailing-whitespace)

; fix spacing at end of sentences
(setq sentence-end-double-space nil)

; Character
(setq-default line-spacing 1)

; Unique names in buffers...
;; (require 'uniquify)
(setq uniquify-buffer-name-style 'reverse)
(setq uniquify-separator "/")
(setq uniquify-after-kill-buffer-p t) ; rename after killing uniquified
(setq uniquify-ignore-buffers-re "^\\*") ; don't muck with special buffers

; load current version of file automatically
(global-auto-revert-mode 1)

; hide tool bar
(tool-bar-mode 0)

; Treat new buffers as text
(setq default-major-mode 'text-mode)

;; alias y to yes and n to no
(defalias 'yes-or-no-p 'y-or-n-p)

; highlight matches from searches
(setq isearch-highlight t)
(setq search-highlight t)
(setq-default transient-mark-mode t)

; indent whole buffer
(defun iwb ()
  "indent whole buffer"
  (interactive)
  (delete-trailing-whitespace)
  (indent-region (point-min) (point-max) nil)
  (untabify (point-min) (point-max)))

(setenv "NO_PROXY" "localhost,127.0.0.1")
(setenv "no_proxy" "localhost,127.0.0.1")

(if (system-is-mac)
  (progn
    (message "on Darwin")
    (add-hook 'c++-mode-hook (lambda () (setq-default flycheck-c/c++-clang-executable "/opt/macports/bin/g++-mp-6")))
    (add-hook 'c++-mode-hook (lambda () (setq-default flycheck-clang-standard-library "libc++")))
    (setq mac-option-modifier 'meta)
    (setq mac-command-modifier 'meta)
    (global-set-key [kp-delete] 'delete-char) ;; sets fn-delete to be right-delete
    (setq ispell-program-name "/opt/local/bin/ispell")
  )
  (progn
    (message "on Linux")
    (setq ispell-program-name (expand-file-name "~/.swx/bin/ispell"))
    (add-hook 'c++-mode-hook (lambda () (setq-default flycheck-c/c++-clang-executable "/projects/sems/install/rhel6-x86_64/sems/compiler/gcc/4.7.2/base/bin/g++" )))
    (add-hook 'c++-mode-hook (lambda () (setq-default flycheck-clang-standard-library "libstdc++")))
  )
)
(add-hook 'c++-mode-hook (lambda () (setq flycheck-clang-language-standard "c++11")))

;; _ is part of word
(modify-syntax-entry ?_ "w")
(add-hook 'python-mode-hook #'(lambda () (modify-syntax-entry ?_ "w")))
(add-hook 'c++-mode-hook #'(lambda () (modify-syntax-entry ?_ "w")))
(add-hook 'c-mode-hook #'(lambda () (modify-syntax-entry ?_ "w")))
(add-hook 'fortran-mode-hook #'(lambda () (modify-syntax-entry ?_ "w")))
(add-hook 'ruby-mode-hook #'(lambda () (modify-syntax-entry ?_ "w")))
(add-hook 'js2-mode-hook #'(lambda () (modify-syntax-entry ?_ "w")))
(add-hook 'lua-mode-hook #'(lambda () (modify-syntax-entry ?_ "w")))

; Reverse options from ispell
(defadvice ispell-command-loop (before ispell-reverse-miss-list activate)
  "reverse the first argument to ispell-command-loop"
  (ad-set-arg 0 (reverse (ad-get-arg 0))))


;; (load-file (expand-file-name "~/.local.d/etc/spacemacs/evil-little-word.el"))
;; (require 'evil-little-word)
