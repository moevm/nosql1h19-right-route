package com.dd.routing


import android.content.Intent
import android.graphics.Color
import android.location.LocationManager
import android.os.Bundle
import android.preference.PreferenceManager
import android.util.Log
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
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

        //TODO: remove underline in search
        // Удаляет иконку поиска из поисковой строки
        (search_view.findViewById(
            resources.getIdentifier(
                "android:id/search_mag_icon",
                null,
                null
            )
        ) as ImageView).layoutParams = LinearLayout.LayoutParams(0, 0)


        // Отображает местоположение
        val provider = GpsMyLocationProvider(this)
        provider.addLocationSource(LocationManager.GPS_PROVIDER)
        //provider.addLocationSource(LocationManager.NETWORK_PROVIDER)
        //provider.addLocationSource(LocationManager.PASSIVE_PROVIDER)
        locationOverlay = MyLocationNewOverlay(provider, map)
        locationOverlay.enableMyLocation()
        map.overlays.add(locationOverlay)


        // Map events overlay
        val mapEventsOverlay = MapEventsOverlay(object : MapEventsReceiver {
            override fun longPressHelper(p: GeoPoint?): Boolean {
                val marker = Marker(map)
                if (markers.size == 2) {
                    map.overlays.remove(markers[0])
                    markers.removeAt(0)
                }
                markers.add(marker)
                marker.position = p
                marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM)
                map.overlays.add(marker)
                map.invalidate()
                return true
            }

            override fun singleTapConfirmedHelper(p: GeoPoint?): Boolean {
                return false
            }
        })
        map.overlays.add(mapEventsOverlay)


        setListeners() // Устанавлеваем слушатели на все
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
                R.id.nav_about -> {
                    startActivity(Intent(this, AboutActivity::class.java))
                }
                R.id.nav_exit -> {
                    AlertDialog.Builder(this)
                        .setMessage(R.string.exit_dialog_text)
                        .setCancelable(false)
                        .setPositiveButton(R.string.yes) { _, _ ->
                            finishAffinity()
                        }.setNegativeButton(R.string.no, null)
                        .show()
                }
            }
            drawer_layout.closeDrawers()
            true
        }


        //TODO: добавить поведение если это понадобится или просто удалить
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
                    // Respond when the drawer motion state changes
                }
            }
        )

        menu_button.setOnClickListener {
            drawer_layout.openDrawer(GravityCompat.START)
        }

        location_button.setOnClickListener {
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
        }


        directions_button.setOnClickListener {
            val url =
                "${VolleyQueue.serverUrl}/api/0.5/fullroute/${markers.first().position.latitude},${markers.first().position.longitude},${markers.last().position.latitude},${markers.last().position.longitude} "
            val jsonObjectRequest = JsonObjectRequest(Request.Method.GET, url, null,
                Response.Listener { response ->
                    drawWays(response)

                },
                Response.ErrorListener { error ->
                    Response.ErrorListener {
                        Log.d("Request", error.message)
                    }
                }
            )
            VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
        }
    }

    private fun drawWays(json: JSONObject) {
        Toast.makeText(this, "Прилетело", Toast.LENGTH_SHORT).show()
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


        map.overlayManager.add(rightWayPolyline)
        map.overlayManager.add(leftWayPolyline)
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
}
