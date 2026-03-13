// ═══════════════════════════════════════════════════════════════════════
//  Wollumetric Renderer — TouchDesigner GLSL TOP  (Fragment Shader)
//
//  Renders any voxelised SOP onto a Wollumetric wiremap display.
//  Each projector pixel is mapped to a world-space position via a
//  pre-computed map texture, then tested against the coloured voxel
//  atlas produced by wollumetric_voxelizer.py.
//
//  Texture inputs
//  ───────────────
//    sTD2DInputs[0]   Map texture   (from createMapTexture.py)
//    sTD2DInputs[1]   RGBA atlas    (from wollumetric_voxelizer.py)
//
//  Vec4 uniforms  (set on the GLSL TOP's Vectors pages)
//  ───────────────
//    uVolumeSize    xyz = display volume extents (printed by
//                   createMapTexture.py as "uVolumeSize")
//    uMeshMin       xyz = voxelised SOP bounding-box minimum
//    uMeshMax       xyz = voxelised SOP bounding-box maximum
//    uVoxelParams   x = voxel resolution  y = slicesPerRow
//                   z = atlas width (px)   w = atlas height (px)
//    uControl       x = debug mode (0–3)
//
//  Debug modes
//  ───────────
//    0  Normal render
//    1  Pass-through map texture
//    2  Pass-through voxel atlas (RGB)
//    3  Show atlas occupancy (alpha channel)
// ═══════════════════════════════════════════════════════════════════════

uniform vec4 uVolumeSize;
uniform vec4 uMeshMin;
uniform vec4 uMeshMax;
uniform vec4 uVoxelParams;
uniform vec4 uControl;

out vec4 fragColor;


void main()
{
    int debugMode = int(uControl.x + 0.5);

    // ── Debug: map texture ─────────────────────────────────────────────
    if (debugMode == 1) {
        vec4 m = texture(sTD2DInputs[0], vUV.st);
        fragColor = TDOutputSwizzle(vec4(m.rgb, 1.0));
        return;
    }

    // ── Debug: voxel atlas colour ──────────────────────────────────────
    if (debugMode == 2) {
        vec4 v = texture(sTD2DInputs[1], vUV.st);
        fragColor = TDOutputSwizzle(vec4(v.rgb, 1.0));
        return;
    }

    // ── Debug: voxel atlas occupancy ───────────────────────────────────
    if (debugMode == 3) {
        float a = texture(sTD2DInputs[1], vUV.st).a;
        fragColor = TDOutputSwizzle(vec4(a, a, a, 1.0));
        return;
    }

    // ── 1. Sample the map texture ──────────────────────────────────────
    vec4 mapColor = texture(sTD2DInputs[0], vUV.st);

    // Black pixels carry no string data
    if (dot(mapColor.rgb, vec3(1.0)) < 0.004) {
        fragColor = vec4(0.0);
        return;
    }

    // Guard: volume size must have been set
    vec3 volSize = uVolumeSize.xyz;
    if (dot(volSize, volSize) < 0.001) {
        fragColor = vec4(0.0);
        return;
    }

    // ── 2. Decode world-space position ─────────────────────────────────
    //  Map texture stores position as RGBA:
    //    R = x (normalised),  G = y high byte,  B = z (normalised),
    //    A = y low byte.   Full y = (G + A / 255.0).
    //  Multiply by volume size to get world coordinates.
    vec3 mapValue = vec3(mapColor.r, mapColor.g + mapColor.a / 255.0, mapColor.b);
    vec3 worldPos = mapValue * volSize;

    // ── 3. Check against the voxelised AABB ────────────────────────────
    vec3 meshMin = uMeshMin.xyz;
    vec3 meshMax = uMeshMax.xyz;
    vec3 range   = meshMax - meshMin;

    if (dot(range, range) < 0.00001) {
        fragColor = vec4(0.0);
        return;
    }

    vec3 uv3 = (worldPos - meshMin) / range;

    if (any(lessThan(uv3, vec3(0.0))) || any(greaterThan(uv3, vec3(1.0)))) {
        fragColor = vec4(0.0);
        return;
    }

    // ── 4. Voxel atlas lookup ──────────────────────────────────────────
    float res          = uVoxelParams.x;
    float slicesPerRow = uVoxelParams.y;
    vec2  atlasSize    = uVoxelParams.zw;

    if (res < 2.0) {
        fragColor = vec4(0.0);
        return;
    }

    // Map normalised position → voxel-grid integer coordinate
    vec3 vc = clamp(floor(uv3 * res), vec3(0.0), vec3(res - 1.0));

    // Atlas tile address for this Z-slice
    float tileCol = mod(vc.z, slicesPerRow);
    float tileRow = floor(vc.z / slicesPerRow);

    // Pixel-centre UV within the atlas
    vec2 atlasUV = vec2(
        (tileCol * res + vc.x + 0.5) / atlasSize.x,
        (tileRow * res + vc.y + 0.5) / atlasSize.y
    );

    vec4 voxelColor = texture(sTD2DInputs[1], atlasUV);

    // ── 5. Output colour ───────────────────────────────────────────────
    if (voxelColor.a > 0.5) {
        fragColor = TDOutputSwizzle(vec4(voxelColor.rgb, 1.0));
    } else {
        fragColor = vec4(0.0);
    }
}
