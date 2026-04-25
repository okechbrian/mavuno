pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "MavunoApp"

include(":app")
include(":agent-app")
include(":buyer-app")
include(":core")
include(":domain")
include(":data")
include(":features")
