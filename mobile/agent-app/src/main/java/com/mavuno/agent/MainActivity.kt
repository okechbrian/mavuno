package com.mavuno.agent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.navigation.compose.rememberNavController
import com.mavuno.agent.navigation.AgentNavGraph
import com.mavuno.core.R
import com.mavuno.domain.repository.HardwarePingRepository
import com.mavuno.features.auth.LoginScreen
import com.mavuno.domain.repository.HardwareScanner
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var hardwareScanner: HardwareScanner

    @Inject
    lateinit var pingRepository: HardwarePingRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                var isAuthenticated by remember { mutableStateOf(false) }

                if (!isAuthenticated) {
                    LoginScreen(
                        role = "Agent",
                        logoResId = R.drawable.ic_agent_logo,
                        onLoginSuccess = { isAuthenticated = true }
                    )
                } else {
                    val navController = rememberNavController()
                    AgentNavGraph(
                        navController = navController,
                        hardwareScanner = hardwareScanner,
                        pingRepository = pingRepository
                    )
                }
            }
        }
    }
}
