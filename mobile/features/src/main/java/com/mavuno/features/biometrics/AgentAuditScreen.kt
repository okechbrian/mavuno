package com.mavuno.features.biometrics

import android.Manifest
import android.content.pm.PackageManager
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BluetoothSearching
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Science
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.mavuno.domain.model.HardwarePing
import java.util.concurrent.Executors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AgentAuditScreen(
    viewModel: AgentAuditViewModel,
    farmId: String
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }

    // State for permission handling
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.CAMERA
            ) == PackageManager.PERMISSION_GRANTED
        )
    }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
        onResult = { granted ->
            hasCameraPermission = granted
            if (granted) {
                viewModel.setCameraMode(true)
            } else {
                viewModel.clearState()
            }
        }
    )

    LaunchedEffect(uiState.error) {
        uiState.error?.let { snackbarHostState.showSnackbar(it) }
    }

    LaunchedEffect(uiState.saveSuccess) {
        if (uiState.saveSuccess) {
            snackbarHostState.showSnackbar("Hardware audit verified and saved to ledger.")
            viewModel.clearState()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Hardware Audit", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1B5E20),
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White
                ),
                actions = {
                    if (uiState.isScanningBluetooth || uiState.isCameraMode || uiState.capturedPing != null) {
                        IconButton(onClick = { viewModel.clearState() }) {
                            Icon(Icons.Default.Close, contentDescription = "Cancel")
                        }
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        containerColor = Color(0xFFF1F8E9)
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            
            if (uiState.isConnecting) {
                Column(
                    modifier = Modifier.fillMaxSize(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    CircularProgressIndicator(color = Color(0xFF1B5E20))
                    Spacer(modifier = Modifier.height(16.dp))
                    Text("Establishing hardware handshake...", color = Color.Gray)
                }
            } else if (uiState.capturedPing != null) {
                // SUCCESS STATE: Showing the verified biometrics
                Column(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(24.dp)
                ) {
                    Text(
                        "Farm: $farmId",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1B5E20)
                    )
                    
                    AuditDataCard(ping = uiState.capturedPing!!)
                    
                    Spacer(modifier = Modifier.weight(1f))
                    
                    Button(
                        onClick = { viewModel.verifyAndSaveHarvest() },
                        modifier = Modifier.fillMaxWidth().height(56.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD35400))
                    ) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Verify & Submit Audit", fontSize = 16.sp)
                    }
                }
            } else if (uiState.isScanningBluetooth) {
                // BLUETOOTH SCANNING STATE
                Column(modifier = Modifier.fillMaxSize()) {
                    Text("Scanning for nearby hardware nodes...", color = Color.Gray, modifier = Modifier.padding(bottom = 16.dp))
                    
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        items(uiState.bluetoothDevices) { device ->
                            Card(
                                modifier = Modifier.fillMaxWidth().clickable { 
                                    viewModel.connectToDevice(device.macAddress, farmId)
                                },
                                colors = CardDefaults.cardColors(containerColor = Color.White),
                                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                            ) {
                                Row(
                                    modifier = Modifier.padding(16.dp).fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(Icons.Default.Science, contentDescription = null, tint = Color(0xFF2E7D32))
                                    Spacer(modifier = Modifier.width(16.dp))
                                    Column {
                                        Text(device.deviceName, fontWeight = FontWeight.Bold)
                                        Text(device.macAddress, fontSize = 12.sp, color = Color.Gray)
                                    }
                                    Spacer(modifier = Modifier.weight(1f))
                                    Text("${device.rssi} dBm", fontSize = 12.sp, color = Color.Gray)
                                }
                            }
                        }
                    }
                }
            } else if (uiState.isCameraMode) {
                // CAMERA SCANNING STATE
                Column(modifier = Modifier.fillMaxSize()) {
                    Text("Point camera at the IoT Node QR Code", color = Color.Gray, modifier = Modifier.padding(bottom = 16.dp))
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .aspectRatio(1f)
                            .background(Color.Black, RoundedCornerShape(16.dp)),
                        contentAlignment = Alignment.Center
                    ) {
                        if (hasCameraPermission) {
                            CameraPreviewView(
                                onBarcodeScanned = { barcodeData ->
                                    viewModel.fallbackCameraScan(barcodeData, farmId)
                                }
                            )
                        } else {
                            Text("Camera permission required", color = Color.White)
                        }
                    }
                }
            } else {
                // DEFAULT START OPTIONS
                Column(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text("Start Hardware Audit", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1B5E20))
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Farm: $farmId", color = Color.Gray, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(48.dp))
                    
                    Button(
                        onClick = { viewModel.startBluetoothScan() },
                        modifier = Modifier.fillMaxWidth().height(64.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1B5E20))
                    ) {
                        Icon(Icons.Default.BluetoothSearching, contentDescription = null)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("Scan Local Bluetooth Nodes", fontSize = 16.sp)
                    }
                    
                    Spacer(modifier = Modifier.height(24.dp))
                    Text("OR", color = Color.Gray, fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(24.dp))
                    
                    OutlinedButton(
                        onClick = {
                            if (hasCameraPermission) {
                                viewModel.setCameraMode(true)
                            } else {
                                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                            }
                        },
                        modifier = Modifier.fillMaxWidth().height(64.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF1B5E20))
                    ) {
                        Icon(Icons.Default.CameraAlt, contentDescription = null)
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("Fallback: Scan Node QR Code", fontSize = 16.sp)
                    }
                }
            }
        }
    }
}

@Composable
fun CameraPreviewView(
    onBarcodeScanned: (String) -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }

    AndroidView(
        factory = { ctx ->
            val previewView = PreviewView(ctx)
            val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)

            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()

                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }

                // Setup ML Kit Barcode Scanner
                val options = BarcodeScannerOptions.Builder()
                    .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                    .build()
                val scanner = BarcodeScanning.getClient(options)

                val imageAnalyzer = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                    .also { analysis ->
                        analysis.setAnalyzer(cameraExecutor) { imageProxy ->
                            processImageProxy(scanner, imageProxy, onBarcodeScanned)
                        }
                    }

                try {
                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(
                        lifecycleOwner,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        preview,
                        imageAnalyzer
                    )
                } catch (exc: Exception) {
                    Log.e("CameraPreview", "Use case binding failed", exc)
                }
            }, ContextCompat.getMainExecutor(ctx))

            previewView
        },
        modifier = Modifier.fillMaxSize()
    )
    
    DisposableEffect(Unit) {
        onDispose {
            cameraExecutor.shutdown()
        }
    }
}

@androidx.annotation.OptIn(androidx.camera.core.ExperimentalGetImage::class)
private fun processImageProxy(
    barcodeScanner: com.google.mlkit.vision.barcode.BarcodeScanner,
    imageProxy: ImageProxy,
    onBarcodeScanned: (String) -> Unit
) {
    val mediaImage = imageProxy.image
    if (mediaImage != null) {
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
        barcodeScanner.process(image)
            .addOnSuccessListener { barcodes ->
                val firstBarcode = barcodes.firstOrNull()?.rawValue
                if (firstBarcode != null) {
                    onBarcodeScanned(firstBarcode)
                }
            }
            .addOnFailureListener {
                Log.e("CameraPreview", "Barcode scanning failed", it)
            }
            .addOnCompleteListener {
                imageProxy.close()
            }
    } else {
        imageProxy.close()
    }
}

@Composable
fun AuditDataCard(ping: HardwarePing) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Verified Soil Biometrics", fontWeight = FontWeight.Bold, fontSize = 16.sp, color = Color(0xFF1B5E20))
            HorizontalDivider(color = Color.LightGray.copy(alpha = 0.5f))
            BiometricRow("Soil Moisture", "${String.format("%.1f", ping.soilMoisture)}%")
            BiometricRow("Soil Temp", "${String.format("%.1f", ping.soilTemperature)}°C")
            BiometricRow("Nitrogen (N)", "${String.format("%.1f", ping.nitrogen)} mg/kg")
            BiometricRow("Phosphorus (P)", "${String.format("%.1f", ping.phosphorus)} mg/kg")
            BiometricRow("Potassium (K)", "${String.format("%.1f", ping.potassium)} mg/kg")
            
            Spacer(modifier = Modifier.height(8.dp))
            Surface(
                color = Color(0xFFF5F5F5),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Cryptographic Signature", fontSize = 10.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                    Text(ping.signature, fontSize = 10.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace, modifier = Modifier.padding(top = 4.dp))
                }
            }
        }
    }
}

@Composable
fun BiometricRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Color.Gray, fontSize = 14.sp)
        Text(value, fontWeight = FontWeight.Bold, color = Color.Black, fontSize = 14.sp)
    }
}
