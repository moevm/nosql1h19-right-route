package com.dd.routing

import android.graphics.Color
import android.location.Geocoder
import android.location.LocationManager
import android.os.Bundle
import android.preference.PreferenceManager
import android.util.Log
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.SearchView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.Request
import com.android.volley.Response
import com.android.volley.toolbox.JsonObjectRequest
import kotlinx.android.synthetic.main.activity_available_area.*
import kotlinx.android.synthetic.main.activity_available_area.location_button
import kotlinx.android.synthetic.main.activity_main_content.map
import kotlinx.android.synthetic.main.activity_main_content.search_view
import org.json.JSONObject
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.BoundingBox
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.CustomZoomButtonsController
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.mylocation.GpsMyLocationProvider
import org.osmdroid.views.overlay.mylocation.MyLocationNewOverlay
import java.io.IOException
import java.util.*
import kotlin.collections.ArrayList

class AvailableAreaActivity : AppCompatActivity() {

    private val areas = ArrayList<Polygon>()
    private lateinit var locationOverlay: MyLocationNewOverlay
    private var searchMarker: Marker? = null

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

        displayAvailableArea()
        setListeners()
    }

    private fun displayAvailableArea() {
        val url = "${getServerUrl(this)}/api/0.5/bounds"
        val jsonObjectRequest = JsonObjectRequest(
            Request.Method.GET, url, null,
            Response.Listener { response ->
                drawAvailableArea(response)
            },
            Response.ErrorListener { error ->
                Response.ErrorListener {
                    Log.d("Request", error.message)
                }
            }
        )
        VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
    }

    private fun drawAvailableArea(json: JSONObject) {
        if (json.getBoolean("error")) {
            Toast.makeText(this, json.getString("msg"), Toast.LENGTH_LONG).show()
            return
        }
        areas.forEach {
            map.overlayManager.remove(it)
        }
        areas.clear()
        val bounds = json.getJSONObject("data").getJSONArray("bounds")
        for (i in 0 until bounds.length()) {
            val area = bounds.getJSONObject(i)
            val polygon = Polygon()
            polygon.fillColor = Color.argb(64, 0, 255, 0)
            polygon.strokeWidth = 0.0f
            polygon.points = arrayListOf(
                GeoPoint(area.getDouble("minlat"), area.getDouble("minlon")),
                GeoPoint(area.getDouble("maxlat"), area.getDouble("minlon")),
                GeoPoint(area.getDouble("maxlat"), area.getDouble("maxlon")),
                GeoPoint(area.getDouble("minlat"), area.getDouble("maxlon"))
            )
            areas.add(polygon)
            map.overlayManager.add(polygon)
            map.invalidate()
        }
        zoomToAvailableArea()
    }

    private fun zoomToAvailableArea() {
        if (areas.isEmpty()) {
            return
        }
        val points = areas.flatMap { polygon ->
            polygon.points
        }
        map.zoomToBoundingBox(
            BoundingBox(
                points.maxBy { it.latitude }!!.latitude,
                points.maxBy { it.longitude }!!.longitude,
                points.minBy { it.latitude }!!.latitude,
                points.minBy { it.longitude }!!.longitude
            ), true
        )
    }


    private fun addSearchMarker(point: GeoPoint) {
        if (searchMarker != null) {
            map.overlays.remove(searchMarker)
            searchMarker = null
        }
        searchMarker = Marker(map)
        searchMarker?.icon = getDrawable(R.drawable.ic_marker_search)
        searchMarker?.setOnMarkerClickListener { marker, mapView ->
            mapView.overlays.remove(marker)
            searchMarker = null
            mapView.invalidate()
            true
        }
        searchMarker?.position = point
        searchMarker?.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
        map.overlays.add(searchMarker)
        map.invalidate()
        //close_button.visibility = View.VISIBLE
    }

    private fun setListeners() {

        search_view.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                search_view.clearFocus()
                if (query !== null) {
                    val geocoder = Geocoder(this@AvailableAreaActivity, Locale.ROOT)
                    try {
                        val boundingBox = map.boundingBox
                        geocoder.getFromLocationName(
                            query,
                            1,
                            boundingBox.latSouth,
                            boundingBox.lonWest,
                            boundingBox.latNorth,
                            boundingBox.lonEast
                        ).firstOrNull()?.let {
                            addSearchMarker(GeoPoint(it.latitude, it.longitude))
                            map.zoomToBoundingBox(
                                BoundingBox(
                                    it.latitude + 0.02,
                                    it.longitude + 0.02,
                                    it.latitude - 0.02,
                                    it.longitude - 0.02
                                ), true
                            )
                        }
                    } catch (e: IOException) {
                        Toast.makeText(this@AvailableAreaActivity, getText(R.string.no_connection), Toast.LENGTH_SHORT).show()
                    } catch (e: IllegalArgumentException) {

                    }
                }
                return true
            }

            override fun onQueryTextChange(newText: String?): Boolean {
                return true
            }

        })

        back_button.setOnClickListener {
            onBackPressed()
        }

        refresh_button.setOnClickListener {
            displayAvailableArea()
        }

        location_button.setOnClickListener {
            try {
                val location = locationOverlay.myLocation
                if (locationOverlay.isMyLocationEnabled) {
                    map.zoomToBoundingBox(
                        BoundingBox(
                            location.latitude + 0.02,
                            location.longitude + 0.02,
                            location.latitude - 0.02,
                            location.longitude - 0.02
                        ), true
                    )
                }
            } catch (e: Exception) {
                showLocation()
            }
        }
    }


    private fun showLocation() {
        if (::locationOverlay.isInitialized) {
            if (locationOverlay.isMyLocationEnabled) {
                return
            }
            map.overlays.remove(locationOverlay)
        }
        val provider = GpsMyLocationProvider(this)
        provider.addLocationSource(LocationManager.GPS_PROVIDER)
        locationOverlay = MyLocationNewOverlay(provider, map)
        locationOverlay.enableMyLocation()
        map.overlays.add(locationOverlay)
        map.invalidate()
    }
}
