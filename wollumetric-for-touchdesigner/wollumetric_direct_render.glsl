// ═══════════════════════════════════════════════════════════════════════
//  Wollumetric Direct Renderer — TouchDesigner GLSL TOP  (Fragment Shader)
//
//  Renders coloured scene geometry directly onto the projector output
//  without any voxelisation step.  For each output pixel the map
//  texture provides the exact 3D world position; a ray is then cast
//  through the triangle data to determine inside/outside (even–odd
//  rule) and the colour is taken from the nearest surface intersection.
//
//  Result is exact and deterministic.
//
//  Texture inputs
//  ───────────────
//    sTD2DInputs[0]   Map texture   (from createMapTexture.py)
//    sTD2DInputs[1]   Triangle data (from wollumetric_gpu_voxelizer.py)
//                     Width = numTriangles, Height = 6, RGBA32F
//                     Row 0–2: vertex A / B / C positions  (x, y, z, 0)
//                     Row 3–5: vertex A / B / C colours    (r, g, b, 1)
//
//  Vec4 uniforms  (set on the GLSL TOP's Vectors pages)
//  ───────────────
//    uVolumeSize    xyz = display volume extents (from createMapTexture.py)
//    uTriParams     x = numTriangles
//    uMeshMin       xyz = bounding-box minimum (from tri_data output pars)
//    uMeshMax       xyz = bounding-box maximum (from tri_data output pars)
//    uControl       x = debug mode (0–3)
//
//  Debug modes
//  ───────────
//    0  Normal render
//    1  Pass-through map texture
//    2  Show inside/outside mask (white = inside)
//    3  Show nearest-surface distance (greyscale)
// ═══════════════════════════════════════════════════════════════════════

uniform vec4 uVolumeSize;
uniform vec4 uTriParams;
uniform vec4 uMeshMin;
uniform vec4 uMeshMax;
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

    // ── 1. Sample the map texture ──────────────────────────────────────
    vec4 mapColor = texture(sTD2DInputs[0], vUV.st);

    // Black pixels carry no string data
    if (dot(mapColor.rgb, vec3(1.0)) < 0.004) {
        fragColor = vec4(0.0);
        return;
    }

    vec3 volSize = uVolumeSize.xyz;
    if (dot(volSize, volSize) < 0.001) {
        fragColor = vec4(0.0);
        return;
    }

    // ── 2. Decode world-space position ─────────────────────────────────
    vec3 mapValue = vec3(mapColor.r,
                         mapColor.g + mapColor.a / 255.0,
                         mapColor.b);
    vec3 worldPos = mapValue * volSize;

    // ── 3. Early AABB reject ───────────────────────────────────────────
    int numTris = int(uTriParams.x + 0.5);
    vec3 meshMin = uMeshMin.xyz;
    vec3 meshMax = uMeshMax.xyz;

    if (numTris == 0) {
        fragColor = vec4(0.0);
        return;
    }

    // Only check Y and Z against AABB — X is the ray direction
    if (worldPos.y < meshMin.y || worldPos.y > meshMax.y ||
        worldPos.z < meshMin.z || worldPos.z > meshMax.z) {
        fragColor = vec4(0.0);
        return;
    }

    // ── 4. Ray-cast: even-odd inside/outside test along +X ─────────────
    float cx = worldPos.x;
    float rayY = worldPos.y;
    float rayZ = worldPos.z;

    int   crossLeft   = 0;
    int   crossRight  = 0;
    float closestDist = 1e30;
    float closestU    = 0.0;
    float closestV    = 0.0;
    int   closestTri  = -1;

    float midX = (meshMin.x + meshMax.x) * 0.5;

    for (int i = 0; i < numTris; i++) {
        vec3 A = texelFetch(sTD2DInputs[1], ivec2(i, 0), 0).xyz;
        vec3 B = texelFetch(sTD2DInputs[1], ivec2(i, 1), 0).xyz;
        vec3 C = texelFetch(sTD2DInputs[1], ivec2(i, 2), 0).xyz;

        // Per-triangle YZ AABB early exit
        float triMinY = min(A.y, min(B.y, C.y));
        float triMaxY = max(A.y, max(B.y, C.y));
        if (rayY < triMinY || rayY > triMaxY) continue;

        float triMinZ = min(A.z, min(B.z, C.z));
        float triMaxZ = max(A.z, max(B.z, C.z));
        if (rayZ < triMinZ || rayZ > triMaxZ) continue;

        // Barycentric solve in YZ plane
        vec2 e0 = C.yz - A.yz;
        vec2 e1 = B.yz - A.yz;
        vec2 e2 = vec2(rayY, rayZ) - A.yz;

        float d00 = dot(e0, e0);
        float d01 = dot(e0, e1);
        float d02 = dot(e0, e2);
        float d11 = dot(e1, e1);
        float d12 = dot(e1, e2);

        float denom = d00 * d11 - d01 * d01;
        if (abs(denom) < 1e-7) continue;

        float inv = 1.0 / denom;
        float u = (d11 * d02 - d01 * d12) * inv;
        float v = (d00 * d12 - d01 * d02) * inv;

        if (u < 0.0 || v < 0.0 || u + v > 1.0) continue;

        float hitX = A.x + u * (C.x - A.x) + v * (B.x - A.x);

        if (hitX < cx) crossLeft++;
        if (hitX > cx) crossRight++;

        float dist = abs(hitX - cx);
        if (dist < closestDist) {
            closestDist = dist;
            closestU    = u;
            closestV    = v;
            closestTri  = i;
        }
    }

    // ── 5. Determine inside/outside ────────────────────────────────────
    int crossings = (cx < midX) ? crossLeft : crossRight;
    bool isInside = (crossings & 1) == 1;

    // ── Debug: inside/outside mask ─────────────────────────────────────
    if (debugMode == 2) {
        float m = isInside ? 1.0 : 0.0;
        fragColor = TDOutputSwizzle(vec4(m, m, m, 1.0));
        return;
    }

    // ── Debug: nearest surface distance ────────────────────────────────
    if (debugMode == 3) {
        float d = clamp(1.0 - closestDist * 2.0, 0.0, 1.0);
        fragColor = TDOutputSwizzle(vec4(d, d, d, 1.0));
        return;
    }

    // ── 6. Output colour ───────────────────────────────────────────────
    if (isInside && closestTri >= 0) {
        float w = 1.0 - closestU - closestV;
        vec3 cA = texelFetch(sTD2DInputs[1], ivec2(closestTri, 3), 0).xyz;
        vec3 cB = texelFetch(sTD2DInputs[1], ivec2(closestTri, 4), 0).xyz;
        vec3 cC = texelFetch(sTD2DInputs[1], ivec2(closestTri, 5), 0).xyz;
        vec3 col = w * cA + closestV * cB + closestU * cC;
        fragColor = TDOutputSwizzle(vec4(col, 1.0));
    } else {
        fragColor = vec4(0.0);
    }
}
