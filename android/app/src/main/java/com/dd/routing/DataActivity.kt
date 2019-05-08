package com.dd.routing

import android.os.Bundle
import android.preference.PreferenceManager
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.DefaultRetryPolicy
import com.android.volley.Request
import com.android.volley.Response
import com.android.volley.toolbox.StringRequest
import kotlinx.android.synthetic.main.activity_data.*
import kotlinx.android.synthetic.main.activity_main_content.map
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory
import org.osmdroid.util.GeoPoint
import org.osmdroid.views.CustomZoomButtonsController

class DataActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_data)

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

        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = resources.getString(R.string.data_activity_title)


        setListeners()
    }


    private fun setListeners() {
        toolbar.setNavigationOnClickListener {
            onBackPressed()
        }

        backup_button.setOnClickListener {
            val urlBuilder = StringBuilder(getServerUrl(this))
                .append("/api/0.5/create_backup")
            val stringRequest = StringRequest(
                Request.Method.GET, urlBuilder.toString(),
                Response.Listener {},
                Response.ErrorListener {
                    Toast.makeText(this, "Backup error", Toast.LENGTH_SHORT).show()
                }
            )
            stringRequest.retryPolicy = DefaultRetryPolicy(100000, 0, DefaultRetryPolicy.DEFAULT_BACKOFF_MULT)
            VolleyQueue.getInstance(this).addToRequestQueue(stringRequest)
        }

        restore_button.setOnClickListener {
            val urlBuilder = StringBuilder(getServerUrl(this))
                .append("/api/0.5/load_backup")
            val stringRequest = StringRequest(
                Request.Method.GET, urlBuilder.toString(),
                Response.Listener {},
                Response.ErrorListener {
                    Toast.makeText(this, "Restore error", Toast.LENGTH_SHORT).show()
                }
            )
            stringRequest.retryPolicy = DefaultRetryPolicy(100000, 0, DefaultRetryPolicy.DEFAULT_BACKOFF_MULT)
            VolleyQueue.getInstance(this).addToRequestQueue(stringRequest)
        }

        import_button.setOnClickListener {
            val boundingBox = map.boundingBox
            val urlBuilder = StringBuilder(getServerUrl(this))
                .append("/api/0.5/load_map")
                .append("?min_lat=${boundingBox.latSouth}")
                .append("&min_lon=${boundingBox.lonWest}")
                .append("&max_lat=${boundingBox.latNorth}")
                .append("&max_lon=${boundingBox.lonEast}")
            val stringRequest = StringRequest(
                Request.Method.GET, urlBuilder.toString(),
                Response.Listener {},
                Response.ErrorListener {
                    Toast.makeText(this, "Import error", Toast.LENGTH_SHORT).show()
                }
            )
            stringRequest.retryPolicy = DefaultRetryPolicy(100000, 0, DefaultRetryPolicy.DEFAULT_BACKOFF_MULT)
            VolleyQueue.getInstance(this).addToRequestQueue(stringRequest)
        }
    }
}
