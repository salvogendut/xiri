/* SGI SCREEN-SAVER 1.0, used by IRIX xlock -besaver. Included by Xext/saver.c. */
static RESTYPE sgiSaverType;
static int sgiEventBase;

static void
sgiSaverNotify(ScreenPtr screen, Bool active)
{
    SetupScreen(screen);
    xEvent event = { 0 };

    if (active == pPriv->sgiActive)
        return;
    pPriv->sgiActive = active;
    event.u.u.type = sgiEventBase + (active ? 0 : 1);
    event.u.destroyNotify.event = screen->myNum; /* CARD32 at wire offset 4 */
    WriteEventsToClient(pPriv->sgiClient, 1, &event);
}

static void
sgiSwapEvent(xEvent *from, xEvent *to)
{
    *to = *from;
    cpswaps(from->u.u.sequenceNumber, to->u.u.sequenceNumber);
    cpswapl(from->u.destroyNotify.event, to->u.destroyNotify.event);
}

static int
sgiRelease(pointer value, XID id)
{
    ScreenPtr screen = value;
    SetupScreen(screen);

    if (pPriv && pPriv->sgiResource == id) {
        if (pPriv->sgiActive && (*screen->SaveScreen)(screen, SCREEN_SAVER_ON))
            screen->screensaver.blanked = SCREEN_IS_BLANKED;
        pPriv->sgiClient = NULL;
        pPriv->sgiResource = None;
        pPriv->sgiActive = FALSE;
        CheckScreenPrivate(screen);
    }
    return Success;
}

static int
sgiDispatch(ClientPtr client)
{
    REQUEST(xReq);
    /* SGI puts the two 16-bit version numbers at offsets 4 and 6.
     * Enable and Disable use the usual zero reply length at offset 4. */
    struct {
        CARD8 type, status;
        CARD16 sequence, major, minor;
        CARD32 pad[6];
    } reply = { 0 };
    ScreenPtr screen;
    ScreenSaverScreenPrivatePtr priv;
    CARD32 number;
    int rc, n;

    reply.type = X_Reply;
    reply.sequence = client->sequence;
    switch (stuff->data) {
    case 0:
        REQUEST_SIZE_MATCH(xReq);
        reply.major = 1;
        break;
    case 1:
    case 2:
        REQUEST_SIZE_MATCH(xResourceReq);
        number = ((xResourceReq *)stuff)->id;
        if (client->swapped)
            swapl(&number, n);
        if (number >= screenInfo.numScreens)
            break;
        screen = screenInfo.screens[number];
        rc = XaceHook(XACE_SCREENSAVER_ACCESS, client, screen, DixSetAttrAccess);
        if (rc != Success)
            return rc;
        priv = GetScreenPrivate(screen);
        if (stuff->data == 2) {
            if (priv && priv->sgiClient == client) {
                FreeResource(priv->sgiResource, RT_NONE);
                reply.status = 1;
            }
            break;
        }
        if (priv && (priv->sgiClient || priv->attr))
            break;
        priv = MakeScreenPrivate(screen);
        if (!priv)
            return BadAlloc;
        priv->sgiResource = FakeClientID(client->index);
        if (!AddResource(priv->sgiResource, sgiSaverType, screen))
            return BadAlloc;
        priv->sgiClient = client;
        reply.status = 1;
        if (screenIsSaved == SCREEN_SAVER_ON) {
            /* Uncover a display that the core had already blanked. */
            if (screen->screensaver.blanked == SCREEN_IS_BLANKED)
                (*screen->SaveScreen)(screen, SCREEN_SAVER_OFF);
            else if (HasSaverWindow(screen)) {
                screen->screensaver.pWindow = NullWindow;
                FreeResource(screen->screensaver.wid, RT_NONE);
            }
            screen->screensaver.blanked = SCREEN_ISNT_SAVED;
            sgiSaverNotify(screen, TRUE);
        }
        break;
    default:
        return BadRequest;
    }
    if (client->swapped) {
        swaps(&reply.sequence, n);
        swaps(&reply.major, n);
    }
    WriteToClient(client, sizeof(reply), &reply);
    return Success;
}

static void
sgiSaverInit(void)
{
    ExtensionEntry *ext;

    sgiSaverType = CreateNewResourceType(sgiRelease, "SGISaverClient");
    if (!sgiSaverType)
        return;
    ext = AddExtension("SCREEN-SAVER", 2, 0, sgiDispatch, sgiDispatch,
                       NULL, StandardMinorOpcode);
    if (ext) {
        sgiEventBase = ext->eventBase;
        EventSwapVector[sgiEventBase] = sgiSwapEvent;
        EventSwapVector[sgiEventBase + 1] = sgiSwapEvent;
    }
}
