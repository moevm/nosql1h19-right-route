package com.dd.routing

import android.app.Activity
import android.content.Context
import android.preference.PreferenceManager
import android.view.View
import android.view.inputmethod.InputMethodManager
import androidx.appcompat.app.AppCompatActivity


fun getServerUrl(context: Context): String {
    val preferences = PreferenceManager.getDefaultSharedPreferences(context)
    return preferences.getString("serverUrl", VolleyQueue.serverUrl) ?: VolleyQueue.serverUrl
}

fun setServerUrl(context: Context, url: String) {
    val preferences = PreferenceManager.getDefaultSharedPreferences(context)
    preferences.edit().apply {
        putString("serverUrl", url)
        apply()
    }
}


fun hideKeyboard(activity: AppCompatActivity) {
    val imm = activity.getSystemService(Activity.INPUT_METHOD_SERVICE) as InputMethodManager
    var view = activity.currentFocus
    if (view == null) {
        view = View(activity)
    }
    imm.hideSoftInputFromWindow(view.windowToken, 0)
}

