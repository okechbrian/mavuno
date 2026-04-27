package com.mavuno.app.navigation

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import com.mavuno.features.farmer.FarmerDashboardScreen
import com.mavuno.features.history.Transaction
import com.mavuno.features.history.TransactionHistoryScreen
import com.mavuno.features.social.SocialFeedScreen
import com.mavuno.features.training.TrainingScreen
import com.mavuno.features.training.TrainingViewModel
import com.mavuno.features.verification.QrScannerScreen
import com.mavuno.features.verification.TokenVerifier
import com.mavuno.features.verification.VerificationResult

sealed class Screen(val route: String, val label: String = "", val icon: ImageVector? = null) {
    object Dashboard : Screen("dashboard", "Home", Icons.Default.Home)
    object Community : Screen("social", "Social", Icons.Default.Groups)
    object Scanner : Screen("scanner", "Scan", Icons.Default.QrCodeScanner)
    object History : Screen("history", "History", Icons.Default.History)
    object Training : Screen("training", "Training", Icons.Default.Home)
}

@Composable
fun MavunoNavGraph(
    navController: NavHostController,
    tokenVerifier: TokenVerifier,
    farmId: String,
    startDestination: String = Screen.Dashboard.route
) {
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
                FarmerDashboardScreen(
                    viewModel = hiltViewModel(),
                    farmId = farmId,
                    onNavigateToTraining = { navController.navigate(Screen.Training.route) }
                )
            }

            composable(Screen.Community.route) {
                SocialFeedScreen(
                    viewModel = hiltViewModel(),
                    userRole = "farmer"
                )
            }

            composable(Screen.Training.route) {
                val viewModel: TrainingViewModel = hiltViewModel()
                TrainingScreen(
                    viewModel = viewModel,
                    onBack = { navController.popBackStack() }
                )
            }

            composable(Screen.Scanner.route) {
                QrScannerScreen(
                    onTokenScanned = { data ->
                        val result = tokenVerifier.verifyToken(data)
                        if (result is VerificationResult.Success) {
                            navController.navigate(Screen.Dashboard.route)
                        }
                    },
                    onBack = { navController.popBackStack() }
                )
            }

            composable(Screen.History.route) {
                TransactionHistoryScreen(
                    title = "Farmer History",
                    transactions = listOf(
                        Transaction("1", "ECT Disbursed", "+25.00 ECT", System.currentTimeMillis() - 86400000, "Settled"),
                        Transaction("2", "Crop Offer", "500 KG", System.currentTimeMillis() - 172800000, "Open")
                    )
                )
            }
        }
    }
}

@Composable
fun BottomNavigationBar(navController: NavHostController) {
    val items = listOf(Screen.Dashboard, Screen.Community, Screen.History)
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
                            popUpTo(navController.graph.startDestinationId)
                            launchSingleTop = true
                        }
                    }
                )
            }
        }
    }
}
