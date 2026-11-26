/* Read the Newport screen's current mode for the IRIX Display control panel. */
#include <sys/endian.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "xorg-server.h"
#include "xf86.h"
#include "xf86Module.h"
#include "xf86cmap.h"
#include "xf86Modes.h"
#include "dixstruct.h"
#include "extnsionst.h"
#include "globals.h"

enum vc_request {
    Version = 0, VcScreenInfo = 1, FormatList = 2, ChannelInfo = 8,
    MonitorName = 9, QueryControl = 11, OutputSync = 13, SyncSource = 15, PlatformParameter = 17,
    GammaMaps = 18, GammaMap = 19, StoreGamma8 = 20, StoreGamma16 = 21, GammaColors = 22, SelectEvents = 23, ChannelRectangle = 24,
    NvFormatList = 30
};

/* The request and reply bodies are in the client's X byte order. */
static uint32_t
get32(ClientPtr cl, const uint8_t *p)
{
    uint32_t v;
    memcpy(&v, p, sizeof(v));
    return cl->swapped ? bswap32(v) : v;
}

static void
put16(ClientPtr cl, uint8_t *p, uint16_t v)
{
    if (cl->swapped) v = bswap16(v);
    memcpy(p, &v, sizeof(v));
}

static void
put32(ClientPtr cl, uint8_t *p, uint32_t v)
{
    if (cl->swapped) v = bswap32(v);
    memcpy(p, &v, sizeof(v));
}

/* The fixed format descriptor is followed by a padded name and a field
 * descriptor. Newport's Indy screen is a progressive, single-field mode. */
static size_t
format(ClientPtr cl, uint8_t *p, const DisplayModeRec *m)
{
    char name[40];
    uint32_t mhz = (uint32_t)(xf86ModeVRefresh(m) * 1000.0 + 0.5);
    snprintf(name, sizeof(name), "%dx%d_%u", m->HDisplay, m->VDisplay,
        (mhz + 500) / 1000);
    size_t len = strlen(name) + 1;
    size_t padded = (len + 3) & ~(size_t)3;

    put16(cl, p, m->HDisplay);
    put16(cl, p+2, m->VDisplay);
    put16(cl, p+4, m->HTotal);
    put16(cl, p+6, m->VTotal);
    put32(cl, p+8, mhz);
    put32(cl, p+12, mhz);
    put32(cl, p+16, (uint32_t)m->Clock * 1000);
    put32(cl, p+20, m->HTotal - m->HSyncEnd);
    put32(cl, p+24, m->HSyncEnd - m->HSyncStart);
    put32(cl, p+28, m->HSyncStart - m->HDisplay);
    put32(cl, p+32, m->HDisplay);
    put32(cl, p+40, len);
    put32(cl, p+44, 1);
    memcpy(p+48, name, len);

    uint8_t *field = p+48+padded;
    put32(cl, field+4, 1); /* consecutive lines */
    put32(cl, field+8, (m->VTotal - m->VSyncEnd) * m->HTotal);
    put32(cl, field+12, (m->VSyncEnd - m->VSyncStart) * m->HTotal);
    put32(cl, field+20, (m->VSyncStart - m->VDisplay) * m->HTotal);
    put32(cl, field+24, m->VDisplay * m->HTotal);
    put32(cl, field+28, 7); /* RGB */
    put32(cl, field+32, 3); /* both eyes */
    return 48+padded+36;
}

static int
dispatch(ClientPtr cl)
{
    const uint8_t *req = cl->requestBuffer;
    uint8_t reply[32+256*2] = { X_Reply, TRUE };
    size_t size = 32;
    unsigned op = req[1];
    if (cl->req_len < 2)
        return BadLength;
    put16(cl, reply+2, cl->sequence);
    if (op == Version) {
        if (cl->req_len != 2) return BadLength;
        put16(cl, reply+8, 1);
        put16(cl, reply+10, 0);
    } else {
        uint32_t screen = get32(cl, req+4);
        if (screen >= (uint32_t)screenInfo.numScreens) return BadValue;
        ScrnInfoPtr scr = xf86Screens[screen];
        DisplayModePtr m = scr->currentMode;
        if (!m || !scr->driverName || strcasecmp(scr->driverName, "newport"))
            return BadMatch;
        int gamma = xf86GetGammaRampSize(scr->pScreen) == 256;
        xf86MsgVerb(X_INFO, 5, "SGI-VIDEO-CONTROL request %u (%lu words)\n",
            op, cl->req_len);
        switch (op) {
        case VcScreenInfo:
            if (cl->req_len != 2) return BadLength;
            put32(cl, reply+8, 1); /* one channel */
            put32(cl, reply+12, 1); /* per-channel format enumeration */
            memcpy(reply+32, "ng1", 3);
            size += 4;
            break;
        case ChannelInfo:
            if (cl->req_len != 3) return BadLength;
            if (get32(cl, req+8) != 0) return BadValue;
            /* The viewport coordinates are in signed 20.12 fixed-point pixels. */
            put32(cl, reply+16, m->HDisplay * 4096);
            put32(cl, reply+20, m->VDisplay * 4096);
            put32(cl, reply+28, gamma);
            put32(cl, reply+56, UINT32_MAX);
            size = 76 + format(cl, reply+76, m) + 4 * gamma;
            break;
        case FormatList:
        case NvFormatList:
            if (cl->req_len < 6) return BadLength;
            if (get32(cl, req+8) != 0) return BadValue;
            if (get32(cl, req+16) && !get32(cl, req+20) &&
                !(op == NvFormatList && req[13])) {
                put32(cl, reply+8, 1);
                put32(cl, reply+12, 1);
                size += format(cl, reply+32, m);
            }
            break;
        case GammaMaps:
            if (cl->req_len != 2) return BadLength;
            put32(cl, reply+8, gamma);
            break;
        case GammaMap:
            if (cl->req_len != 3) return BadLength;
            if (!gamma || get32(cl, req+8)) return BadValue;
            put32(cl, reply+8, 256);
            put32(cl, reply+12, 8);
            put32(cl, reply+16, LocalClient(cl) ? 0 : 4);
            break;
        case StoreGamma8:
        case StoreGamma16: {
            uint16_t ramp[3][256];
            if (cl->req_len < 5) return BadLength;
            const unsigned n = get32(cl, req+12), mask = get32(cl, req+16);
            unsigned bytes = op == StoreGamma16 ? 2 : 1;
            if (!gamma || get32(cl, req+8) || n > 256 || !mask || (mask & ~7U))
                return BadValue;
            if (cl->req_len != 5 + (n * bytes + 3) / 4) return BadLength;
            if (!LocalClient(cl)) return BadAccess;
            int rc = xf86GetGammaRamp(scr->pScreen, 256, ramp[0], ramp[1], ramp[2]);
            if (rc != Success) return rc;
            for (unsigned i = 0; i < n; i++) {
                uint16_t value;
                if (bytes == 1) {
                    value = req[20+i] * 257;
                } else {
                    memcpy(&value, req+20+2*i, sizeof(value));
                    if (cl->swapped) value = bswap16(value);
                }
                for (unsigned c = 0; c < 3; c++)
                    if (mask & (1U << c)) ramp[c][i] = value;
            }
            return xf86ChangeGammaRamp(scr->pScreen, 256, ramp[0], ramp[1], ramp[2]);
        }
        case GammaColors: {
            uint16_t ramp[3][256];
            if (cl->req_len != 4) return BadLength;
            unsigned component = get32(cl, req+12);
            if (!gamma || get32(cl, req+8) || component < 1 || component > 3)
                return BadValue;
            int rc = xf86GetGammaRamp(scr->pScreen, 256, ramp[0], ramp[1], ramp[2]);
            if (rc != Success) return rc;
            put32(cl, reply+8, 256);
            for (int i = 0; i < 256; i++)
                put16(cl, reply+32+2*i, ramp[component-1][i]);
            size += 512;
            break;
        }
        case PlatformParameter:
            if (cl->req_len < 5) return BadLength;
            reply[1] = FALSE;
            break;
        case QueryControl:
            if (cl->req_len != 4) return BadLength;
            if (get32(cl, req+8) != 0) return BadValue;
            reply[1] = gamma && get32(cl, req+12) == 10;
            break; /* map zero is active */
        case OutputSync:
        case MonitorName:
            if (cl->req_len != 3) return BadLength;
            if (get32(cl, req+8) != 0) return BadValue;
            reply[1] = FALSE;
            break;
        case SyncSource:
            if (cl->req_len != 2) return BadLength;
            reply[1] = FALSE;
            break;
        case SelectEvents:
            if (cl->req_len != 3) return BadLength;
            /* With a fixed mode this screen generates no change events. */
            return Success;
        case ChannelRectangle:
            if (cl->req_len != 8) return BadLength;
            if (get32(cl, req+8) != 0) return BadValue;
            if (req[28]) return BadAccess;
            put32(cl, reply+16, m->HDisplay * 4096);
            put32(cl, reply+20, m->VDisplay * 4096);
            break;
        default:
            return BadRequest;
        }
    }
    put32(cl, reply+4, (size-32)/4);
    WriteToClient(cl, size, reply);
    return Success;
}

static void
init(void)
{
    AddExtension("SGI-VIDEO-CONTROL", 1, 0, dispatch, dispatch, NULL,
        StandardMinorOpcode);
}

static ExtensionModule ext = {init, "SGI-VIDEO-CONTROL", NULL, NULL, NULL};
static XF86ModuleVersionInfo version = {
    "sgivc", "Xiri", MODINFOSTRING1, MODINFOSTRING2, XORG_VERSION_CURRENT,
    1, 0, 0, ABI_CLASS_EXTENSION, ABI_EXTENSION_VERSION, MOD_CLASS_EXTENSION, {0}
};

static pointer
setup(pointer module, pointer options, int *major, int *minor)
{
    (void)options; (void)major; (void)minor;
    LoadExtension(&ext, FALSE);
    return module;
}

_X_EXPORT XF86ModuleData sgivcModuleData = {&version, setup, NULL};
