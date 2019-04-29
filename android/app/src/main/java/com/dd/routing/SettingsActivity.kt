package com.dd.routing

import android.os.Bundle
import android.util.Patterns
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import kotlinx.android.synthetic.main.activity_settings.*

class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = resources.getString(R.string.settings_activity_title)

        server_url.setText(getServerUrl(this))

        setListeners()
    }


    private fun setListeners() {
        toolbar.setNavigationOnClickListener {
            onBackPressed()
        }

        save_button.setOnClickListener {
            if (Patterns.WEB_URL.matcher(server_url.text.toString()).matches()) {
                setServerUrl(this, server_url.text.toString())
                Toast.makeText(this, "Saved", Toast.LENGTH_LONG).show()
                hideKeyboard(this)
            } else {
                Toast.makeText(this, "Incorrect url", Toast.LENGTH_LONG).show()
            }

        }
    }

}
