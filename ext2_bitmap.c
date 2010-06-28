/*
 * ext2_bitmap.c
 *
 *  Created on: 22/06/2010
 *      Author: Pedro Peña Pérez
 */

#include <stdio.h>
#include <ext2fs/ext2fs.h>

struct ext2fs_struct_generic_bitmap {
        errcode_t       magic;
        ext2_filsys     fs;
        __u32           start, end;
        __u32           real_end;
        char    *       description;
        char    *       bitmap;
        errcode_t       base_error_code;
        __u32           reserved[7];
};

int main(int argc, char **argv) {
	ext2_filsys fs;
    ext2fs_generic_bitmap bitmap;
    size_t size;

	ext2fs_open(argv[1], 0, 0, 0, unix_io_manager, &fs);
	ext2fs_read_bitmaps(fs);
    ext2fs_get_mem(sizeof(struct ext2fs_struct_generic_bitmap), &bitmap);
	memcpy(bitmap, fs->block_map, sizeof(struct ext2fs_struct_generic_bitmap));
	size = (size_t) (((bitmap->real_end - bitmap->start) / 8) + 1);
	printf("sBlock: %u\n", fs->blocksize);
	printf("sBitmap: %u\n", bitmap->real_end - bitmap->start + 1);
	printf("bitmap: ");
	fwrite(bitmap->bitmap, 1, size, stdout);
	ext2fs_close(fs);

	return 0;
}
