package com.dd.routing

import android.os.Bundle
import android.preference.PreferenceManager
import android.widget.ImageView
import android.widget.LinearLayout
import androidx.appcompat.app.AppCompatActivity
import kotlinx.android.synthetic.main.activity_available_area.*
import kotlinx.android.synthetic.main.activity_main_content.map
import kotlinx.android.synthetic.main.activity_main_content.search_view
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.CustomZoomButtonsController

class AvailableAreaActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_available_area)

        //Setup mapView
        Configuration.getInstance()
            .load(applicationContext, PreferenceManager.getDefaultSharedPreferences(applicationContext))
        map.apply {
            setTileSource(TileSourceFactory.MAPNIK)
            setMultiTouchControls(true)
            minZoomLevel = 3.0
            maxZoomLevel = 20.0
            controller.setZoom(5.0)
            controller.setCenter(GeoPoint(59.991149, 30.318757))
            zoomController.setVisibility(CustomZoomButtonsController.Visibility.NEVER)
        }


        // Удаляет иконку поиска из поисковой строки
        (search_view.findViewById(
            resources.getIdentifier(
                "android:id/search_mag_icon",
                null,
                null
            )
        ) as ImageView).layoutParams = LinearLayout.LayoutParams(0, 0)

        setListeners()
    }


    private fun setListeners() {
        back_button.setOnClickListener {
            onBackPressed()
        }
    }
}
