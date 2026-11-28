/* SGI Media Recorder 6.5.30f calls this ViewKit preflight in its main-window
 * constructor, even for -allowmenu audio. The microphone launcher selects
 * that mode before loading this object. Screen capture uses the vendor DSO. */
extern char *getenv(const char *);
extern int putenv(char *);
extern char *strstr(const char *, const char *);

int
overlayPlanesAvailable__16VkScreenSelectorSGP10_WidgetRec(void *widget)
{
    char *restore = getenv("XIRI_RECORDER_RESTORE");

    (void)widget;
    /* Restore the original DSO list before the recorder starts any helpers. */
    return restore != 0 &&
        strstr(restore, "_RLDN32_LIST=") == restore &&
        putenv(restore) == 0;
}
