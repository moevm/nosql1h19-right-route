package com.dd.routing


import android.content.Intent
import android.graphics.Color
import android.location.Address
import android.location.Geocoder
import android.location.LocationManager
import android.os.Bundle
import android.preference.PreferenceManager
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
import org.osmdroid.views.overlay.Polyline
import org.osmdroid.views.overlay.mylocation.GpsMyLocationProvider
import org.osmdroid.views.overlay.mylocation.MyLocationNewOverlay


class MainActivity : AppCompatActivity() {

    lateinit var locationOverlay: MyLocationNewOverlay
    val markers = ArrayList<Marker>()
    private val routes = ArrayList<Polyline>()


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
                val marker = Marker(map)
                if (markers.size == 2) {
                    map.overlays.remove(markers[0])
                    markers.removeAt(0)
                }
                markers.add(marker)
                markers.first().title = "Start"
                markers.last().title = "End"
                marker.position = p
                marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                map.overlays.add(marker)
                map.invalidate()
                close_button.visibility = View.VISIBLE
                if (p != null) {
                    getNameFromLocation(p)
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
        setListeners() // Устанавлеваем слушатели на все
    }


    private fun getNameFromLocation(point: GeoPoint) {
//      val geocoder = GeocoderNominatim(BuildConfig.APPLICATION_ID)
//      val list = geocoder.getFromLocation(point.latitude, point.longitude, 10)
        val geocoder = Geocoder(this)
        val addresses = geocoder.getFromLocation(point.latitude, point.longitude, 1)
        if (addresses.isNotEmpty()) {
            showPointInfo(addresses.first())
        }
    }


    private fun showPointInfo(address: Address) {
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


    private fun hidePointInfo() {
        info_layout.findViewById<LinearLayout>(R.id.point_info_layout).visibility = View.GONE
    }


    private fun showRoutesInfo(json: JSONObject) {
        val routesInfoLayout = info_layout.findViewById<GridLayout>(R.id.routes_info_layout)

        val leftDistance = json.getDouble("distance_left")
        val rightDistance = json.getDouble("distance_right")

        if (leftDistance < 1.0) {
            routesInfoLayout.findViewById<TextView>(R.id.left_route_stats).text =
                getString(R.string.distance_in_m, leftDistance.times(1000).toInt())
        } else {
            routesInfoLayout.findViewById<TextView>(R.id.left_route_stats).text =
                getString(R.string.distance_in_km, String.format("%.1f", leftDistance))
        }

        if (rightDistance < 1.0) {
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

    private fun setListeners() {
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
            val urlBuilder = StringBuilder(getServerUrl(this))
            when (markers.size) {
                0 -> {
                    Toast.makeText(this, "Недостаточно точек", Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
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
                        return@setOnClickListener
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
                    return@setOnClickListener
                }
            }


            val jsonObjectRequest = JsonObjectRequest(Request.Method.GET, urlBuilder.toString(), null,
                Response.Listener { response ->
                    drawRoutes(response)

                },
                Response.ErrorListener {
                    Toast.makeText(this, "ОШИБКА ААА", Toast.LENGTH_SHORT).show()
                }
            )

            jsonObjectRequest.retryPolicy = DefaultRetryPolicy(50000, 0, DefaultRetryPolicy.DEFAULT_BACKOFF_MULT)


            Toast.makeText(this, "Полетел запрос", Toast.LENGTH_SHORT).show()
            VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
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

    private fun drawRoutes(json: JSONObject) {
        Toast.makeText(this, "Прилетело", Toast.LENGTH_SHORT).show()
        clearRoutes()
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

    private fun clearRoutes() {
        routes.forEach {
            map.overlays.remove(it)
        }
        routes.clear()
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
