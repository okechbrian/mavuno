package com.mavuno.agent.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import com.mavuno.domain.repository.HardwarePingRepository
import com.mavuno.features.biometrics.AgentAuditScreen
import com.mavuno.features.biometrics.AgentDashboardScreen
import com.mavuno.domain.repository.HardwareScanner
import com.mavuno.features.disbursement.EctDisbursementScreen
import com.mavuno.features.social.SocialFeedScreen

sealed class Screen(val route: String, val label: String = "", val icon: ImageVector? = null) {
    object Dashboard : Screen("dashboard", "Dashboard", Icons.Default.Home)
    object Audit : Screen("audit", "Audit", Icons.Default.Analytics)
    object Disbursement : Screen("disbursement", "Disburse", Icons.Default.Payments)
    object Community : Screen("social", "Social", Icons.Default.Groups)
}

@Composable
fun AgentNavGraph(
    navController: NavHostController,
    hardwareScanner: HardwareScanner,
    pingRepository: HardwarePingRepository,
    startDestination: String = Screen.Dashboard.route
) {
    var selectedFarmId by remember { mutableStateOf<String?>(null) }

    Scaffold(
        bottomBar = {
            BottomNavigationBar(navController)
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = startDestination,
            modifier = Modifier.fillMaxSize().padding(innerPadding)
        ) {
            composable(Screen.Dashboard.route) {
                AgentDashboardScreen(
                    viewModel = hiltViewModel(),
                    onNavigateToAudit = { farmId ->
                        selectedFarmId = farmId
                        navController.navigate(Screen.Audit.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    onNavigateToDisburse = { farmId ->
                        selectedFarmId = farmId
                        navController.navigate(Screen.Disbursement.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }

            composable(Screen.Audit.route) {
                if (selectedFarmId != null) {
                    AgentAuditScreen(
                        viewModel = hiltViewModel(),
                        farmId = selectedFarmId!!
                    )
                } else {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("Please select a farm from the Dashboard first.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            composable(Screen.Disbursement.route) {
                if (selectedFarmId != null) {
                    EctDisbursementScreen(
                        viewModel = hiltViewModel(),
                        farmId = selectedFarmId!!,
                        onBack = { navController.popBackStack() }
                    )
                } else {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text("Please select a farm from the Dashboard first.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            composable(Screen.Community.route) {
                SocialFeedScreen(
                    viewModel = hiltViewModel(),
                    userRole = "agent"
                )
            }
        }
    }
}

@Composable
fun BottomNavigationBar(navController: NavHostController) {
    val items = listOf(Screen.Dashboard, Screen.Audit, Screen.Disbursement, Screen.Community)
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    NavigationBar {
        items.forEach { screen ->
            screen.icon?.let { icon ->
                NavigationBarItem(
                    icon = { Icon(icon, contentDescription = screen.label) },
                    label = { Text(screen.label) },
                    selected = currentRoute == screen.route,
                    onClick = {
                        navController.navigate(screen.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }
        }
    }
}
