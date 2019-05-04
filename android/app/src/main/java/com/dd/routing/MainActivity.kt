package com.dd.routing


import android.content.Intent
import android.graphics.Color
import android.location.Address
import android.location.Geocoder
import android.location.LocationManager
import android.os.Bundle
import android.preference.PreferenceManager
import android.util.Log
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.Response
import com.android.volley.toolbox.JsonObjectRequest
import kotlinx.android.synthetic.main.activity_main.*
import kotlinx.android.synthetic.main.activity_main_content.*
import org.json.JSONObject
import org.osmdroid.config.Configuration
import org.osmdroid.events.MapEventsReceiver
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.BoundingBox
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.CustomZoomButtonsController
import org.osmdroid.views.overlay.MapEventsOverlay
import org.osmdroid.views.overlay.Marker
import org.osmdroid.views.overlay.Polygon
import org.osmdroid.views.overlay.Polyline
import org.osmdroid.views.overlay.mylocation.GpsMyLocationProvider
import org.osmdroid.views.overlay.mylocation.MyLocationNewOverlay
import java.io.IOException
import java.util.*
import kotlin.collections.ArrayList


class MainActivity : AppCompatActivity() {

    private lateinit var locationOverlay: MyLocationNewOverlay
    val markers = ArrayList<Marker>()
    private val routes = ArrayList<Polyline>()
    private val areas = ArrayList<Polygon>()
    private var isAvailableAreaShown = false


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

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


        // Map events overlay
        val mapEventsOverlay = MapEventsOverlay(object : MapEventsReceiver {
            override fun longPressHelper(p: GeoPoint?): Boolean {
                if (p != null) {
                    addMarker(p)
                    showPointInfo(getPointInfo(p))
                }
                hideRoutesInfo()
                return true
            }

            override fun singleTapConfirmedHelper(p: GeoPoint?): Boolean {
                return false
            }
        })
        map.overlays.add(mapEventsOverlay)


        showLocation()
        setListeners()
    }

    private fun setListeners() {
        search_view.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                search_view.clearFocus()
                if (query !== null) {
                    val geocoder = Geocoder(this@MainActivity, Locale.ROOT)
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
                            addMarker(GeoPoint(it.latitude, it.longitude))
                            showPointInfo(it)
                        }
                    } catch (e: IOException) {
                        Toast.makeText(this@MainActivity, getText(R.string.no_connection), Toast.LENGTH_SHORT).show()
                    } catch (e: IllegalArgumentException) {

                    }

                }

                return true
            }

            override fun onQueryTextChange(newText: String?): Boolean {
                return true
            }

        })


        available_area_button.setOnClickListener {
            if (isAvailableAreaShown) {
                areas.forEach {
                    map.overlayManager.remove(it)
                }
                areas.clear()
                isAvailableAreaShown = false
                map.invalidate()

            } else {
                displayAvailableArea()
                isAvailableAreaShown = true
            }
        }


        info_layout.findViewById<LinearLayout>(R.id.point_info_layout).findViewById<Button>(R.id.button_routes)
            .setOnClickListener {
                buildRoutes()
            }

        info_layout.setOnClickListener {
            // Чтобы не взаимодействовать с картой позади
        }

        navigation_view.setNavigationItemSelectedListener { menuItem ->
            when (menuItem.itemId) {
                R.id.nav_available_area -> {
                    startActivity(Intent(this, AvailableAreaActivity::class.java))
                }
                R.id.nav_data -> {
                    startActivity(Intent(this, DataActivity::class.java))
                }
                R.id.nav_settings -> {
                    startActivity(Intent(this, SettingsActivity::class.java))
                }
                R.id.nav_about -> {
                    startActivity(Intent(this, AboutActivity::class.java))
                }
                R.id.nav_exit -> {
                    showExitDialog()
                }
            }
            drawer_layout.closeDrawers()
            true
        }


        drawer_layout.addDrawerListener(
            object : DrawerLayout.DrawerListener {
                override fun onDrawerSlide(drawerView: View, slideOffset: Float) {
                    // Respond when the drawer's position changes
                }

                override fun onDrawerOpened(drawerView: View) {
                    // Respond when the drawer is opened
                }

                override fun onDrawerClosed(drawerView: View) {
                    // Respond when the drawer is closed
                }

                override fun onDrawerStateChanged(newState: Int) {
                    search_view.clearFocus()
                }
            }
        )

        menu_button.setOnClickListener {
            drawer_layout.openDrawer(GravityCompat.START)
        }

        location_button.setOnClickListener {
            try {
                if (locationOverlay.isMyLocationEnabled) {
                    val location = locationOverlay.myLocation
                    map.zoomToBoundingBox(
                        BoundingBox(
                            location.latitude + 0.02,
                            location.longitude + 0.02,
                            location.latitude - 0.02,
                            location.longitude - 0.02
                        ), true
                    )
                } else {
                    showLocation()
                    Toast.makeText(this, "Не удается определить местоположение", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                showLocation()
            }
        }

        directions_button.setOnClickListener {
            buildRoutes()
        }

        close_button.setOnClickListener {
            markers.forEach { marker ->
                map.overlays.remove(marker)
            }
            markers.clear()
            map.invalidate()
            hidePointInfo()
            hideRoutesInfo()
            clearRoutes()
            it.visibility = View.GONE
        }
    }

    private fun addMarker(point: GeoPoint) {
        val marker = Marker(map)
        if (markers.size == 2) {
            map.overlays.remove(markers[0])
            markers.removeAt(0)
        }
        markers.add(marker)
        markers.first().title = "Start"
        markers.last().title = "End"
        marker.position = point
        marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
        map.overlays.add(marker)
        map.invalidate()
        close_button.visibility = View.VISIBLE
    }


    private fun getPointInfo(point: GeoPoint): Address? {
        val geocoder = Geocoder(this, Locale.ROOT)
        try {
            val addresses = geocoder.getFromLocation(point.latitude, point.longitude, 1)
            if (addresses.isNotEmpty()) {
                return addresses.first()
            }
        } catch (e: IOException) {
            Toast.makeText(this, getText(R.string.no_connection), Toast.LENGTH_SHORT).show()
        } catch (e: IllegalArgumentException) {

        }
        return null
    }


    private fun showPointInfo(address: Address?) {
        if (address != null) {
            val addressBuilder = StringBuilder()
            addressBuilder.append(address.getAddressLine(0))
            val pointInfoLayout = info_layout.findViewById<LinearLayout>(R.id.point_info_layout)
            pointInfoLayout.findViewById<TextView>(R.id.point_name).text = addressBuilder.toString()
            pointInfoLayout.findViewById<TextView>(R.id.point_location).text =
                getString(
                    R.string.point_location,
                    address.latitude.toFloat().toString(),
                    address.longitude.toFloat().toString()
                )
            pointInfoLayout.visibility = View.VISIBLE
        }
    }


    private fun hidePointInfo() {
        info_layout.findViewById<LinearLayout>(R.id.point_info_layout).visibility = View.GONE
    }


    private fun showRoutesInfo(json: JSONObject) {
        val routesInfoLayout = info_layout.findViewById<GridLayout>(R.id.routes_info_layout)

        val leftDistance = json.getDouble("distance_left")
        val rightDistance = json.getDouble("distance_right")

        if (json.getJSONArray("path_left").length() == 0) {
            routesInfoLayout.findViewById<TextView>(R.id.left_route_stats).text = getString(R.string.not_found)
        } else if (leftDistance < 1.0) {
            routesInfoLayout.findViewById<TextView>(R.id.left_route_stats).text =
                getString(R.string.distance_in_m, leftDistance.times(1000).toInt())
        } else {
            routesInfoLayout.findViewById<TextView>(R.id.left_route_stats).text =
                getString(R.string.distance_in_km, String.format("%.1f", leftDistance))
        }

        if (json.getJSONArray("path_right").length() == 0) {
            routesInfoLayout.findViewById<TextView>(R.id.right_route_stats).text = getString(R.string.not_found)
        } else if (rightDistance < 1.0) {
            routesInfoLayout.findViewById<TextView>(R.id.right_route_stats).text =
                getString(R.string.distance_in_m, rightDistance.times(1000).toInt())
        } else {
            routesInfoLayout.findViewById<TextView>(R.id.right_route_stats).text =
                getString(R.string.distance_in_km, String.format("%.1f", rightDistance))
        }

        routesInfoLayout.visibility = View.VISIBLE
    }

    private fun hideRoutesInfo() {
        info_layout.findViewById<GridLayout>(R.id.routes_info_layout).visibility = View.GONE
    }


    private fun displayAvailableArea() {
        val url = "${getServerUrl(this)}/api/0.5/bounds"
        val jsonObjectRequest = JsonObjectRequest(
            Request.Method.GET, url, null,
            Response.Listener { response ->
                drawArea(response)
            },
            Response.ErrorListener { error ->
                Response.ErrorListener {
                    Log.d("Request", error.message)
                }
            }
        )
        VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
    }

    private fun drawArea(json: JSONObject) {
        areas.forEach {
            map.overlayManager.remove(it)
        }
        areas.clear()
        val bounds = json.getJSONArray("bounds")
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
    }


    private fun drawRoutes(json: JSONObject) {
        val rightWayJSON = json.getJSONArray("path_right")
        val rightWayPoints = ArrayList<GeoPoint>()
        for (i in 0 until rightWayJSON.length()) {
            rightWayPoints.add(
                GeoPoint(
                    rightWayJSON.getJSONObject(i).getDouble("lat"),
                    rightWayJSON.getJSONObject(i).getDouble("lon")
                )
            )
        }
        val rightWayPolyline = Polyline()
        rightWayPolyline.setPoints(rightWayPoints)
        rightWayPolyline.color = Color.RED
        rightWayPolyline.width = 8.0f

        val leftWayJSON = json.getJSONArray("path_left")
        val leftWayPoints = ArrayList<GeoPoint>()
        for (i in 0 until leftWayJSON.length()) {
            leftWayPoints.add(
                GeoPoint(
                    leftWayJSON.getJSONObject(i).getDouble("lat"),
                    leftWayJSON.getJSONObject(i).getDouble("lon")
                )
            )
        }
        val leftWayPolyline = Polyline()
        leftWayPolyline.setPoints(leftWayPoints)
        leftWayPolyline.color = Color.BLUE
        leftWayPolyline.width = 15.0f

        map.overlayManager.add(leftWayPolyline)
        map.overlayManager.add(rightWayPolyline)
        map.invalidate()

        routes.add(rightWayPolyline)
        routes.add(leftWayPolyline)

        hidePointInfo()
        showRoutesInfo(json)
    }


    private fun buildRoutes() {
        clearRoutes()
        val urlBuilder = StringBuilder(getServerUrl(this))
        when (markers.size) {
            0 -> {
                Toast.makeText(this, "Недостаточно точек", Toast.LENGTH_SHORT).show()
                return
            }
            1 -> {
                if (locationOverlay.isMyLocationEnabled) {
                    val location = locationOverlay.myLocation
                    urlBuilder
                        .append("/api/0.5/fullroute")
                        .append("?lat1=${location.latitude}")
                        .append("&lon1=${location.longitude}")
                        .append("&lat2=${markers.last().position.latitude}")
                        .append("&lon2=${markers.last().position.longitude}")

                } else {
                    showLocation()
                    Toast.makeText(this, "Не удается определить местоположение", Toast.LENGTH_SHORT).show()
                    return
                }
            }
            2 -> {
                urlBuilder
                    .append("/api/0.5/fullroute")
                    .append("?lat1=${markers.first().position.latitude}")
                    .append("&lon1=${markers.first().position.longitude}")
                    .append("&lat2=${markers.last().position.latitude}")
                    .append("&lon2=${markers.last().position.longitude}")
            }
            else -> {
                Toast.makeText(this, "Что-то пошло не так", Toast.LENGTH_SHORT).show()
                return
            }
        }


        val jsonObjectRequest = JsonObjectRequest(Request.Method.GET, urlBuilder.toString(), null,
            Response.Listener { response ->
                drawRoutes(response)

            },
            Response.ErrorListener {
                Toast.makeText(this, "Error", Toast.LENGTH_SHORT).show()
            }
        )

        jsonObjectRequest.retryPolicy = DefaultRetryPolicy(50000, 0, DefaultRetryPolicy.DEFAULT_BACKOFF_MULT)


        Toast.makeText(this, "Полетел запрос", Toast.LENGTH_SHORT).show()
        VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
    }

    private fun clearRoutes() {
        routes.forEach {
            map.overlays.remove(it)
        }
        routes.clear()
        map.invalidate()
    }


    override fun onResume() {
        super.onResume()
        map.onResume()
    }

    override fun onPause() {
        super.onPause()
        map.onPause()
    }

    override fun onBackPressed() {
        if (drawer_layout.isDrawerOpen(GravityCompat.START)) {
            drawer_layout.closeDrawers()
        } else {
            showExitDialog()
        }
    }

    private fun showExitDialog() {
        AlertDialog.Builder(this)
            .setMessage(R.string.exit_dialog_text)
            .setCancelable(false)
            .setPositiveButton(R.string.yes) { _, _ ->
                finishAffinity()
            }.setNegativeButton(R.string.no, null)
            .show()
    }

    private fun showLocation() {
        if (::locationOverlay.isInitialized) {
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
