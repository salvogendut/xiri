#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_FONT_FORMATS_H
#include <stdio.h>
int main(int argc,char **argv)
{
 FT_Library lib;FT_Face face;int major,minor,patch;
 const char *path=argc>1?argv[1]:"/usr/X11R7/lib/X11/fonts/Type1/courb.pfa";
 if(FT_Init_FreeType(&lib))return 2;
 FT_Library_Version(lib,&major,&minor,&patch);
 printf("FREETYPE %d.%d.%d\n",major,minor,patch);
 for(int n=0;n<6;n++){
  if(FT_New_Face(lib,path,0,&face))return 3;
  printf("FACE n=%d family=%s style=%s format=%s upem=%u bbox=%ld,%ld,%ld,%ld asc=%d desc=%d height=%d\n",n,face->family_name,face->style_name,FT_Get_Font_Format(face),face->units_per_EM,face->bbox.xMin,face->bbox.yMin,face->bbox.xMax,face->bbox.yMax,face->ascender,face->descender,face->height);
  if(FT_Set_Pixel_Sizes(face,0,20))return 4;
  printf("SIZE ppem=%u,%u scale=%ld,%ld asc=%ld desc=%ld height=%ld\n",face->size->metrics.x_ppem,face->size->metrics.y_ppem,face->size->metrics.x_scale,face->size->metrics.y_scale,face->size->metrics.ascender,face->size->metrics.descender,face->size->metrics.height);
  for(const char *p="Mg";*p;p++){
   if(FT_Load_Char(face,(unsigned char)*p,FT_LOAD_RENDER))return 5;
   printf("GLYPH char=%c advance=%ld,%ld bitmap=%u,%u left=%d top=%d\n",*p,face->glyph->advance.x,face->glyph->advance.y,face->glyph->bitmap.width,face->glyph->bitmap.rows,face->glyph->bitmap_left,face->glyph->bitmap_top);
  }
  FT_Done_Face(face);
 }
 FT_Done_FreeType(lib);return 0;
}
