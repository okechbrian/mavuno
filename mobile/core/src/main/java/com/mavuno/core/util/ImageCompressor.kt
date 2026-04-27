package com.mavuno.core.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream

object ImageCompressor {

    /**
     * Compresses an image from a Uri into a WebP file for low-bandwidth upload.
     * Returns the compressed file.
     */
    fun compressToWebp(context: Context, uri: Uri, targetSizeKb: Int = 200): File {
        val inputStream = context.contentResolver.openInputStream(uri)
        val originalBitmap = BitmapFactory.decodeStream(inputStream)
        
        val outputDir = context.cacheDir
        val compressedFile = File.createTempFile("harvest_", ".webp", outputDir)
        
        var quality = 90
        var stream = ByteArrayOutputStream()
        
        // Initial compression
        originalBitmap.compress(Bitmap.CompressFormat.WEBP, quality, stream)
        
        // Aggressive downscaling if still too large for rural networks
        while (stream.toByteArray().size / 1024 > targetSizeKb && quality > 10) {
            stream = ByteArrayOutputStream()
            quality -= 10
            originalBitmap.compress(Bitmap.CompressFormat.WEBP, quality, stream)
        }
        
        val fos = FileOutputStream(compressedFile)
        fos.write(stream.toByteArray())
        fos.flush()
        fos.close()
        
        return compressedFile
    }
}
