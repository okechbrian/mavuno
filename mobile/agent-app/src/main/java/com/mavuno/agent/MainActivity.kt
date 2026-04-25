package com.mavuno.agent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.mavuno.domain.repository.HardwarePingRepository
import com.mavuno.features.auth.LoginScreen
import com.mavuno.features.biometrics.AgentAuditScreen
import com.mavuno.features.biometrics.HardwareScanner
import com.mavuno.features.disbursement.EctDisbursementScreen
import com.mavuno.features.history.Transaction
import com.mavuno.features.history.TransactionHistoryScreen
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import com.mavuno.core.R

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
                    AgentMainScreen(hardwareScanner, pingRepository)
                }
            }
        }
    }
}

sealed class AgentScreen(val route: String, val label: String, val icon: ImageVector) {
    object Audit : AgentScreen("audit", "Audit", Icons.Default.Analytics)
    object Disbursement : AgentScreen("disbursement", "Disburse", Icons.Default.Payments)
    object History : AgentScreen("history", "History", Icons.AutoMirrored.Filled.List)
}

@Composable
fun AgentMainScreen(hardwareScanner: HardwareScanner, pingRepository: HardwarePingRepository) {
    val navController = rememberNavController()
    val farmId = "UG-MBL-0001"

    Scaffold(
        bottomBar = {
            AgentBottomBar(navController)
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = AgentScreen.Audit.route,
            modifier = Modifier.fillMaxSize().padding(innerPadding)
        ) {
            composable(AgentScreen.Audit.route) {
                AgentAuditScreen(
                    hardwareScanner = hardwareScanner,
                    repository = pingRepository,
                    farmId = farmId
                )
            }
            composable(AgentScreen.Disbursement.route) {
                EctDisbursementScreen(
                    viewModel = hiltViewModel(),
                    farmId = farmId,
                    onBack = { navController.popBackStack() }
                )
            }
            composable(AgentScreen.History.route) {
                TransactionHistoryScreen(
                    title = "Agent Activity",
                    transactions = listOf(
                        Transaction("A1", "Farm Audit", "UG-MBL-0001", System.currentTimeMillis() - 3600000, "Verified"),
                        Transaction("A2", "ECT Disbursement", "25.00 ECT", System.currentTimeMillis() - 7200000, "Signed")
                    )
                )
            }
        }
    }
}

@Composable
fun AgentBottomBar(navController: NavHostController) {
    val items = listOf(AgentScreen.Audit, AgentScreen.Disbursement, AgentScreen.History)
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    NavigationBar {
        items.forEach { screen ->
            NavigationBarItem(
                icon = { Icon(screen.icon, contentDescription = screen.label) },
                label = { Text(screen.label) },
                selected = currentRoute == screen.route,
                onClick = {
                    navController.navigate(screen.route) {
                        popUpTo(navController.graph.startDestinationId)
                        launchSingleTop = true
                    }
                }
            )
        }
    }
}
