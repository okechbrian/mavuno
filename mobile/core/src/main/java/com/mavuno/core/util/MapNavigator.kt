package com.mavuno.core.util

import android.content.Context
import android.content.Intent
import android.net.Uri

object MapNavigator {
    /**
     * Opens the default Map application at the specified coordinates.
     */
    fun openMapAt(context: Context, lat: Double, lng: Double, label: String = "Farm Location") {
        val gmmIntentUri = Uri.parse("geo:$lat,$lng?q=$lat,$lng($label)")
        val mapIntent = Intent(Intent.ACTION_VIEW, gmmIntentUri)
        mapIntent.setPackage("com.google.android.apps.maps")
        if (mapIntent.resolveActivity(context.packageManager) != null) {
            context.startActivity(mapIntent)
        } else {
            // Fallback for non-Google Maps devices
            val intent = Intent(Intent.ACTION_VIEW, gmmIntentUri)
            context.startActivity(intent)
        }
    }
}
