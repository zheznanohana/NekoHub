package com.nekohub.app.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    // 可配置的服务器地址 - 默认值需要用户配置
    var BASE_URL = "http://YOUR_SERVER_IP:5000/api/"
        private set
    
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }
    
    private var authToken: String? = null
    
    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .addInterceptor { chain ->
            val original = chain.request()
            
            val request = original.newBuilder()
                .method(original.method, original.body)
                .apply {
                    authToken?.let { token ->
                        header("Authorization", "Bearer $token")
                    }
                    header("Content-Type", "application/json")
                }
                .build()
            
            chain.proceed(request)
        }
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
    
    private var retrofit = createRetrofit()
    
    val api: NekoHubApi = retrofit.create(NekoHubApi::class.java)
    
    private fun createRetrofit(): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
    
    fun setServerUrl(url: String) {
        BASE_URL = if (url.endsWith("/api/")) url else "$url/api/"
        retrofit = createRetrofit()
    }
    
    fun setToken(token: String) {
        authToken = token
    }
    
    fun clearToken() {
        authToken = null
    }
}
