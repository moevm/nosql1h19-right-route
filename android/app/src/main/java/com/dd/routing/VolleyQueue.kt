package com.dd.routing

import android.content.Context
import androidx.appcompat.app.AppCompatActivity
import com.android.volley.Request
import com.android.volley.RequestQueue
import com.android.volley.toolbox.Volley

class VolleyQueue constructor(context: Context) {

    companion object {
        @Volatile
        private var INSTANCE: VolleyQueue? = null
        const val serverUrl = "http://80.240.18.20:9000"

        fun getInstance(context: Context) =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: VolleyQueue(context).also {
                    INSTANCE = it
                }
            }
    }


    private val requestQueue: RequestQueue by lazy {
        Volley.newRequestQueue(context.applicationContext)
    }

    fun <T> addToRequestQueue(req: Request<T>) {
        requestQueue.add(req)
    }


}