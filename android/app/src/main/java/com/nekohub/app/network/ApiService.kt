package com.nekohub.app.network

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

data class LoginRequest(val username: String, val password: String)
data class LoginResponse(val access_token: String, val message: String = "")
data class Message(
    val id: Int,
    val title: String,
    val content: String,
    val timestamp: String,
    val isRead: Boolean
)
data class Task(
    val id: Int,
    val name: String,
    val type: String,
    val enabled: Boolean
)

interface NekoHubApi {
    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse
    
    @POST("auth/change-password")
    suspend fun changePassword(@Body request: Map<String, String>)
    
    @GET("messages")
    suspend fun getMessages(@Query("limit") limit: Int = 50): List<Message>
    
    @POST("messages/{id}/read")
    suspend fun markMessageRead(@Path("id") id: Int)
    
    @GET("tasks")
    suspend fun getTasks(): List<Task>
    
    @POST("tasks")
    suspend fun createTask(@Body task: Map<String, Any>)
    
    @DELETE("tasks/{id}")
    suspend fun deleteTask(@Path("id") id: Int)
    
    @POST("ai/chat")
    suspend fun chat(@Body request: Map<String, Any>): Map<String, Any>
    
    @GET("settings")
    suspend fun getSettings(): Map<String, Any>
    
    @POST("settings")
    suspend fun updateSettings(@Body settings: Map<String, Any>)
}
