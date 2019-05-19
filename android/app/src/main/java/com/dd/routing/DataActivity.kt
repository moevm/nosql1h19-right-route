package com.dd.routing

import android.os.Bundle
import android.preference.PreferenceManager
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.Request
import com.android.volley.Response
import com.android.volley.toolbox.JsonObjectRequest
import kotlinx.android.synthetic.main.activity_data.*
import kotlinx.android.synthetic.main.activity_main_content.map
import org.json.JSONObject
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
            val jsonObjectRequest = JsonObjectRequest(
                Request.Method.GET, urlBuilder.toString(), null,
                Response.Listener {
                    saveOperationId(it)
                },
                Response.ErrorListener {
                    Toast.makeText(this, "Backup error", Toast.LENGTH_SHORT).show()
                }
            )
            VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
        }

        restore_button.setOnClickListener {
            val urlBuilder = StringBuilder(getServerUrl(this))
                .append("/api/0.5/load_backup")
            val jsonObjectRequest = JsonObjectRequest(
                Request.Method.GET, urlBuilder.toString(), null,
                Response.Listener {
                    saveOperationId(it)
                },
                Response.ErrorListener {
                    Toast.makeText(this, "Restore error", Toast.LENGTH_SHORT).show()
                }
            )
            VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
        }

        import_button.setOnClickListener {
            val boundingBox = map.boundingBox
            val urlBuilder = StringBuilder(getServerUrl(this))
                .append("/api/0.5/load_map")
                .append("?min_lat=${boundingBox.latSouth}")
                .append("&min_lon=${boundingBox.lonWest}")
                .append("&max_lat=${boundingBox.latNorth}")
                .append("&max_lon=${boundingBox.lonEast}")
            val jsonObjectRequest = JsonObjectRequest(
                Request.Method.GET, urlBuilder.toString(), null,
                Response.Listener {
                    saveOperationId(it)
                },
                Response.ErrorListener {
                    Toast.makeText(this, "Import error", Toast.LENGTH_SHORT).show()
                }
            )
            VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
        }
    }

    private fun saveOperationId(json: JSONObject) {
        Toast.makeText(this, json.getString("msg"), Toast.LENGTH_SHORT).show()
        if (json.getBoolean("error")) {
            return
        }
        val preferences = PreferenceManager.getDefaultSharedPreferences(this)
        preferences.edit().apply {
            putString("operationId", json.getJSONObject("data").getString("id"))
            apply()
        }
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.actionbar_status_button, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem?): Boolean {
        if (item?.itemId == R.id.info_button) {
            val preferences = PreferenceManager.getDefaultSharedPreferences(this)
            val operationId = preferences.getString("operationId", VolleyQueue.serverUrl) ?: return true
            val urlBuilder = StringBuilder(getServerUrl(this))
                .append("/api/0.5/check?id=$operationId")
            val jsonObjectRequest = JsonObjectRequest(
                Request.Method.GET, urlBuilder.toString(), null,
                Response.Listener {
                    Toast.makeText(this, it.getString("msg"), Toast.LENGTH_SHORT).show()
                },
                Response.ErrorListener {
                    Toast.makeText(this, "Info error", Toast.LENGTH_SHORT).show()
                }
            )
            VolleyQueue.getInstance(this).addToRequestQueue(jsonObjectRequest)
            return true
        }
        return super.onOptionsItemSelected(item)
    }
}
