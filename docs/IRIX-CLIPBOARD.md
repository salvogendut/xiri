# Copying text between NetBSD and IRIX applications

Native and original IRIX applications in a Xiri desktop use the same Xorg
display. They can exchange text through ordinary X11 selections. No extra
compatibility syscall, imported resource or clipboard daemon is needed for
the workflows below.

## Mouse selection and middle-button paste

Drag with the left mouse button to select text in winterm or native NetBSD
xterm. Click the middle mouse button in the destination terminal to paste it.
This uses **PRIMARY**, the current mouse selection. Both directions are
covered by the [clipboard checks](results/2026-11-13-clipboard.md).

Selecting different text replaces PRIMARY. It does not necessarily replace
the text stored by an application's Copy command.

## Explicit Copy and Paste

In the supplied original gedit, use **Edit → Select All**, **Edit → Copy**
(`Ctrl+C`) and **Edit → Paste** (`Ctrl+V`). This version has no Ctrl+A shortcut
shown for Select All. Copy and Paste use **CLIPBOARD**, separately from PRIMARY.

The image's native xterm 397 does not bind Ctrl+Shift+C to Copy by default.
For a native terminal that selects and pastes through CLIPBOARD, start:

```sh
/usr/X11R7/bin/xterm -xrm '*selectToClipboard: true'
```

In that window, select text with the mouse and paste with the middle button.
The setting applies to that xterm invocation. Its text exchanges with gedit's
Copy/Paste commands pass in both directions. The ordinary xterm and winterm
mouse workflow continues to use PRIMARY.

In a terminal, Ctrl+C normally interrupts the running program; use the mouse
workflow described above.

## Lifetime, users and text formats

The source application supplies selection data when another application asks
for it. The desktop does not start a clipboard manager. After gedit exits,
its CLIPBOARD owner disappears; keeping copied text after its source closes
is not guaranteed. Native terminals may also retain a legacy cut buffer
within the current X session.

Native xdm resets the display at logout. The checks require PRIMARY,
CLIPBOARD and all eight cut buffers to be empty at the greeter and on the
next user's login. The next user can create and paste fresh selections.
Clipboard contents are not saved desktop-session state.

ASCII, multiline/tab text and Latin-1 characters such as `é`, `è` and `£`
pass the bounded checks. Winterm advertises `STRING`; gedit also advertises
`TEXT` and `COMPOUND_TEXT`, but declines `UTF8_STRING`. Full Unicode conversion,
image/rich-text transfer, clipboard history and integration with the host
machine's clipboard remain separate work. The current result covers text
between applications inside the guest's Xorg display.

The protocol and terminology follow the
[X Consortium ICCCM selection rules](https://xorg.freedesktop.org/archive/current/doc/xorg-docs/icccm/icccm.html).
The native terminal setting is documented in
[NetBSD's xterm manual](https://man.netbsd.org/xterm.1).
