package com.dd.routing


import android.os.Bundle
import android.preference.PreferenceManager
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import kotlinx.android.synthetic.main.activity_main.*
import kotlinx.android.synthetic.main.activity_main_content.*
import org.osmdroid.config.Configuration
import org.osmdroid.tileprovider.tilesource.TileSourceFactory


class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        //Setup mapView
        Configuration.getInstance()
            .load(applicationContext, PreferenceManager.getDefaultSharedPreferences(applicationContext))
        map.apply {
            setTileSource(TileSourceFactory.MAPNIK)
            setMultiTouchControls(true)
        }


        navigation_view.setNavigationItemSelectedListener { menuItem ->
            //TODO: implement behaviour
            when (menuItem.itemId) {
                R.id.nav_available_area -> {
                }
                R.id.nav_data -> {
                }
                R.id.nav_about -> {
                }
                R.id.nav_exit -> {
                    AlertDialog.Builder(this)
                        .setMessage(R.string.exit_dialog_text)
                        .setCancelable(false)
                        .setPositiveButton(R.string.yes) { dialog, which ->
                            finishAffinity()
                        }.setNegativeButton(R.string.no, null)
                        .show()
                }
                else -> {
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
        //TODO: remove underline in search


        // Удаляет иконку поиска из поисковой строки
        val magId = resources.getIdentifier("android:id/search_mag_icon", null, null)
        val magImage = search_view.findViewById(magId) as ImageView
        magImage.layoutParams = LinearLayout.LayoutParams(0, 0)

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
