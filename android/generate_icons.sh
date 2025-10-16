#!/bin/bash

# Generate Android app icons from SVG
# This script creates placeholder PNG icons in different sizes

# Colors
BLUE="#2196F3"
GOLD="#FFD700"

# Function to create a simple PNG icon using ImageMagick (if available)
# Otherwise creates XML drawable resources

echo "Creating Android app icons..."

# Create values directory for colors
mkdir -p /workspaces/regami/android/app/src/main/res/values

# Create colors.xml
cat > /workspaces/regami/android/app/src/main/res/values/colors.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">#2196F3</color>
    <color name="primary_dark">#1976D2</color>
    <color name="accent">#FFD700</color>
    <color name="white">#FFFFFF</color>
</resources>
EOF

# Icon sizes for different densities
declare -A SIZES
SIZES[mdpi]=48
SIZES[hdpi]=72
SIZES[xhdpi]=96
SIZES[xxhdpi]=144
SIZES[xxxhdpi]=192

# Check if ImageMagick is available
if command -v convert &> /dev/null; then
    echo "ImageMagick found, generating PNG icons..."

    for density in mdpi hdpi xhdpi xxhdpi xxxhdpi; do
        size=${SIZES[$density]}
        outdir="/workspaces/regami/android/app/src/main/res/mipmap-${density}"

        # Create launcher icon
        convert -size ${size}x${size} xc:"$BLUE" \
            -fill white -font Arial-Bold -pointsize $((size/3)) \
            -gravity center -annotate +0+0 "M" \
            "${outdir}/ic_launcher.png"

        # Create round launcher icon
        convert -size ${size}x${size} xc:none \
            -fill "$BLUE" -draw "circle $((size/2)),$((size/2)) $((size/2)),0" \
            -fill white -font Arial-Bold -pointsize $((size/3)) \
            -gravity center -annotate +0+0 "M" \
            "${outdir}/ic_launcher_round.png"

        echo "Created ${size}x${size} icons for ${density}"
    done

    echo "✓ PNG icons created successfully"
else
    echo "ImageMagick not found, using XML drawables only"
    echo "Install ImageMagick to generate PNG fallbacks: apt-get install imagemagick"

    # Create simple XML drawable fallbacks
    for density in mdpi hdpi xhdpi xxhdpi xxxhdpi; do
        outdir="/workspaces/regami/android/app/src/main/res/mipmap-${density}"

        # Create symbolic link to anydpi version
        ln -sf ../mipmap-anydpi-v26/ic_launcher.xml "${outdir}/ic_launcher.xml" 2>/dev/null || true
        ln -sf ../mipmap-anydpi-v26/ic_launcher_round.xml "${outdir}/ic_launcher_round.xml" 2>/dev/null || true
    done

    echo "✓ XML drawable links created"
fi

# Create launcher background
mkdir -p /workspaces/regami/android/app/src/main/res/drawable
cat > /workspaces/regami/android/app/src/main/res/drawable/ic_launcher_background.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="@color/primary"
        android:pathData="M0,0h108v108h-108z"/>
</vector>
EOF

# Create launcher foreground
cat > /workspaces/regami/android/app/src/main/res/drawable/ic_launcher_foreground.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <!-- Dog silhouette -->
    <path
        android:fillColor="@color/white"
        android:pathData="M54,30
            C42,30 32,40 32,52
            C32,54 32,56 33,58
            L30,65
            C29,68 31,71 34,71
            L38,71
            L38,78
            C38,81 40,83 43,83
            C46,83 48,81 48,78
            L48,71
            L60,71
            L60,78
            C60,81 62,83 65,83
            C68,83 70,81 70,78
            L70,71
            L74,71
            C77,71 79,68 78,65
            L75,58
            C76,56 76,54 76,52
            C76,40 66,30 54,30
            Z
            M45,45
            C46.5,45 48,46.5 48,48
            C48,49.5 46.5,51 45,51
            C43.5,51 42,49.5 42,48
            C42,46.5 43.5,45 45,45
            Z
            M63,45
            C64.5,45 66,46.5 66,48
            C66,49.5 64.5,51 63,51
            C61.5,51 60,49.5 60,48
            C60,46.5 61.5,45 63,45
            Z"/>
    <!-- Accessibility indicator (guide dog vest) -->
    <path
        android:fillColor="@color/accent"
        android:pathData="M38,55
            L38,65
            L48,65
            L48,55
            Z
            M60,55
            L60,65
            L70,65
            L70,55
            Z"/>
</vector>
EOF

echo "✓ Launcher background and foreground created"

# Create splash screen (for Android 12+)
mkdir -p /workspaces/regami/android/app/src/main/res/values-v31
cat > /workspaces/regami/android/app/src/main/res/values-v31/themes.xml << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.Regami" parent="Theme.AppCompat.Light.NoActionBar">
        <item name="android:windowSplashScreenBackground">@color/primary</item>
        <item name="android:windowSplashScreenAnimatedIcon">@drawable/ic_launcher_foreground</item>
        <item name="android:windowSplashScreenAnimationDuration">1000</item>
    </style>
</resources>
EOF

echo "✓ Splash screen theme created (Android 12+)"

echo ""
echo "=========================================="
echo "✅ Android icons and splash screen setup complete!"
echo "=========================================="
echo ""
echo "Created:"
echo "  - App icons (all densities)"
echo "  - Launcher background/foreground"
echo "  - Splash screen (Android 12+)"
echo "  - Color resources"
echo ""
echo "Note: For production, replace with professionally designed icons"
echo "Design guidelines: https://developer.android.com/guide/practices/ui_guidelines/icon_design_launcher"
