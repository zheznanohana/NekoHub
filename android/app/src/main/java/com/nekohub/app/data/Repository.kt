package com.nekohub.app.data

import com.nekohub.app.network.ApiClient
import com.nekohub.app.network.LoginRequest
import com.nekohub.app.network.Message
import com.nekohub.app.network.Task

class AuthRepository {
    suspend fun login(username: String, password: String): Result<String> {
        return try {
            val response = ApiClient.api.login(LoginRequest(username, password))
            if (response.access_token.isNotEmpty()) {
                ApiClient.setToken(response.access_token)
                Result.success(response.access_token)
            } else {
                Result.failure(Exception("登录失败"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    fun logout() {
        ApiClient.clearToken()
    }
}

class MessageRepository {
    suspend fun getMessages(limit: Int = 50): Result<List<Message>> {
        return try {
            val messages = ApiClient.api.getMessages(limit)
            Result.success(messages)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun markRead(id: Int): Result<Unit> {
        return try {
            ApiClient.api.markMessageRead(id)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

class TaskRepository {
    suspend fun getTasks(): Result<List<Task>> {
        return try {
            val tasks = ApiClient.api.getTasks()
            Result.success(tasks)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun createTask(name: String, type: String): Result<Task> {
        return try {
            // TODO: 实现创建任务 API
            Result.failure(Exception("未实现"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun deleteTask(id: Int): Result<Unit> {
        return try {
            ApiClient.api.deleteTask(id)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun toggleTask(id: Int, enabled: Boolean): Result<Unit> {
        return try {
            // TODO: 实现切换任务 API
            Result.failure(Exception("未实现"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

class AIRepository {
    suspend fun chat(message: String, domains: List<String> = emptyList(), limit: Int = 10): Result<String> {
        return try {
            val response = ApiClient.api.chat(mapOf(
                "message" to message,
                "domains" to domains,
                "limit" to limit
            ))
            val reply = response["reply"] as? String ?: "无回复"
            Result.success(reply)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
