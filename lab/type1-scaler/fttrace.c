#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_OUTLINE_H
#include FT_BBOX_H
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

FT_Error FT_Set_Char_Size(FT_Face face, FT_F26Dot6 width, FT_F26Dot6 height,
                        FT_UInt xres, FT_UInt yres)
{
    static FT_Error (*real_size)(FT_Face, FT_F26Dot6, FT_F26Dot6, FT_UInt, FT_UInt);
    static unsigned calls;
    if (!real_size) real_size = dlsym(RTLD_NEXT, "FT_Set_Char_Size");
    if (!real_size) abort();
    FT_Error rc = real_size(face,width,height,xres,yres);
    fprintf(stderr,"FTSIZE call=%u face=%p size=%p request=%ld,%ld dpi=%u,%u rc=%d ppem=%u,%u scale=%ld,%ld\n",++calls,(void*)face,(void*)face->size,width,height,xres,yres,rc,face->size->metrics.x_ppem,face->size->metrics.y_ppem,face->size->metrics.x_scale,face->size->metrics.y_scale);
    return rc;
}

FT_Error FT_Load_Glyph(FT_Face face, FT_UInt index, FT_Int32 flags)
{
    static FT_Error (*real_load)(FT_Face, FT_UInt, FT_Int32);
    static unsigned calls, bad;
    if (!real_load) real_load = dlsym(RTLD_NEXT, "FT_Load_Glyph");
    if (!real_load) abort();
    FT_Error rc = real_load(face, index, flags);
    FT_BBox box = {0};
    if (!rc && face->glyph->format == FT_GLYPH_FORMAT_OUTLINE)
        FT_Outline_Get_CBox(&face->glyph->outline, &box);
    calls++;
    if (rc || (!rc && face->glyph->outline.n_points > 4 && box.yMax-box.yMin < 64)) {
        if (++bad < 30) fprintf(stderr, "FTTRACE load call=%u rc=%d face=%s %s index=%u flags=%lx ppem=%u,%u scales=%ld,%ld format=%lx points=%d box=%ld,%ld,%ld,%ld\n", calls,rc,face->family_name,face->style_name,index,(unsigned long)flags,face->size->metrics.x_ppem,face->size->metrics.y_ppem,face->size->metrics.x_scale,face->size->metrics.y_scale,(unsigned long)face->glyph->format,face->glyph->outline.n_points,box.xMin,box.yMin,box.xMax,box.yMax);
    }
    return rc;
}

FT_Error FT_Outline_Get_BBox(FT_Outline *outline, FT_BBox *box)
{
    static FT_Error (*real_bbox)(FT_Outline *, FT_BBox *);
    static unsigned bad;
    if (!real_bbox) real_bbox = dlsym(RTLD_NEXT, "FT_Outline_Get_BBox");
    if (!real_bbox) abort();
    FT_Error rc = real_bbox(outline,box);
    FT_BBox cbox = {0};
    FT_Outline_Get_CBox(outline,&cbox);
    if (rc || (outline->n_points > 4 && box->yMax-box->yMin < 64)) {
        if (++bad < 30) fprintf(stderr,"FTTRACE bbox rc=%d points=%d bbox=%ld,%ld,%ld,%ld cbox=%ld,%ld,%ld,%ld\n",rc,outline->n_points,box->xMin,box->yMin,box->xMax,box->yMax,cbox.xMin,cbox.yMin,cbox.xMax,cbox.yMax);
    }
    return rc;
}
