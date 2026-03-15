// ═══════════════════════════════════════════════════════════════════════
//  Wollumetric GPU Voxelizer — TouchDesigner GLSL TOP  (Fragment Shader)
//
//  Produces a coloured RGBA voxel atlas from triangle data using the
//  scanline even-odd fill algorithm (ray cast along +X).
//
//  Each output pixel represents one voxel in the atlas.  For each
//  voxel, a ray is cast from the voxel centre along +X through every
//  triangle.  The number of crossings determines inside / outside
//  (even-odd rule), and the nearest intersection provides the surface
//  colour via barycentric interpolation of per-vertex Cd.
//
//  Texture inputs
//  ───────────────
//    sTD2DInputs[0]   Triangle data  (from wollumetric_gpu_voxelizer.py)
//                     Width = numTriangles, Height = 6, RGBA32F
//                     Row 0–2: vertex A / B / C positions  (x, y, z, 0)
//                     Row 3–5: vertex A / B / C colours    (r, g, b, 1)
//
//  Vec4 uniforms  (set on the GLSL TOP's Vectors pages)
//  ───────────────
//    uVoxelParams   x = voxel resolution   y = slicesPerRow
//                   z = atlas width (px)    w = atlas height (px)
//    uMeshMin       xyz = bounding-box minimum
//    uMeshMax       xyz = bounding-box maximum
//    uTriParams     x = numTriangles
//
//  Output resolution
//  ─────────────────
//    Set the GLSL TOP's output resolution (Common page) to
//    atlasWidth × atlasHeight via expressions referencing the Script
//    TOP that produces the triangle data.
// ═══════════════════════════════════════════════════════════════════════

uniform vec4 uVoxelParams;
uniform vec4 uMeshMin;
uniform vec4 uMeshMax;
uniform vec4 uTriParams;

out vec4 fragColor;


void main()
{
    float res          = uVoxelParams.x;
    float slicesPerRow = uVoxelParams.y;
    int   numTris      = int(uTriParams.x + 0.5);
    int   iRes         = int(res + 0.5);
    int   iSpr         = int(slicesPerRow + 0.5);

    // ── 1. Atlas pixel → voxel coordinate ──────────────────────────────
    //  Reverse the 2-D tile layout used by the atlas packer.
    //  Each tile is iRes × iRes pixels; tiles are arranged in a grid
    //  of iSpr columns.  Tile (col, row) holds Z-slice tileRow*iSpr+tileCol.
    int ipx = int(gl_FragCoord.x);
    int ipy = int(gl_FragCoord.y);

    int tileCol = ipx / iRes;
    int tileRow = ipy / iRes;
    int voxelX  = ipx - tileCol * iRes;
    int voxelY  = ipy - tileRow * iRes;
    int voxelZ  = tileRow * iSpr + tileCol;

    // Padding region (beyond actual Z-slices) or no data
    if (voxelZ >= iRes || numTris == 0) {
        fragColor = vec4(0.0);
        return;
    }

    // ── 2. Voxel centre in world space ─────────────────────────────────
    vec3 meshMin = uMeshMin.xyz;
    vec3 meshMax = uMeshMax.xyz;
    vec3 step    = (meshMax - meshMin) / res;

    float cx   = meshMin.x + (float(voxelX) + 0.5) * step.x;
    float rayY = meshMin.y + (float(voxelY) + 0.5) * step.y;
    float rayZ = meshMin.z + (float(voxelZ) + 0.5) * step.z;

    // ── 3. Scanline ray: count crossings left and right of cx ────────
    int   crossLeft    = 0;
    int   crossRight   = 0;
    float closestDist  = 1e30;
    float closestU     = 0.0;
    float closestV     = 0.0;
    int   closestTri   = -1;

    float midX = (meshMin.x + meshMax.x) * 0.5;

    for (int i = 0; i < numTris; i++) {
        // Fetch triangle vertex positions
        vec3 A = texelFetch(sTD2DInputs[0], ivec2(i, 0), 0).xyz;
        vec3 B = texelFetch(sTD2DInputs[0], ivec2(i, 1), 0).xyz;
        vec3 C = texelFetch(sTD2DInputs[0], ivec2(i, 2), 0).xyz;

        // Per-triangle YZ AABB early exit
        float triMinY = min(A.y, min(B.y, C.y));
        float triMaxY = max(A.y, max(B.y, C.y));
        if (rayY < triMinY || rayY > triMaxY) continue;

        float triMinZ = min(A.z, min(B.z, C.z));
        float triMaxZ = max(A.z, max(B.z, C.z));
        if (rayZ < triMinZ || rayZ > triMaxZ) continue;

        // Edge vectors projected onto YZ
        vec2 e0 = C.yz - A.yz;
        vec2 e1 = B.yz - A.yz;
        vec2 e2 = vec2(rayY, rayZ) - A.yz;

        float d00 = dot(e0, e0);
        float d01 = dot(e0, e1);
        float d02 = dot(e0, e2);
        float d11 = dot(e1, e1);
        float d12 = dot(e1, e2);

        float denom = d00 * d11 - d01 * d01;
        if (abs(denom) < 1e-7) continue;   // degenerate triangle

        float inv = 1.0 / denom;
        float u = (d11 * d02 - d01 * d12) * inv;
        float v = (d00 * d12 - d01 * d02) * inv;

        if (u < 0.0 || v < 0.0 || u + v > 1.0) continue;   // ray misses

        // Hit — compute X coordinate of intersection
        float hitX = A.x + u * (C.x - A.x) + v * (B.x - A.x);

        if (hitX < cx) crossLeft++;
        if (hitX > cx) crossRight++;

        // Track nearest intersection for colour assignment
        float dist = abs(hitX - cx);
        if (dist < closestDist) {
            closestDist = dist;
            closestU    = u;
            closestV    = v;
            closestTri  = i;
        }
    }

    // ── 4. Output ──────────────────────────────────────────────────────
    int crossings = (cx < midX) ? crossLeft : crossRight;
    bool isInside = (crossings & 1) == 1;

    if (isInside && closestTri >= 0) {
        float w = 1.0 - closestU - closestV;
        vec3 cA = texelFetch(sTD2DInputs[0], ivec2(closestTri, 3), 0).xyz;
        vec3 cB = texelFetch(sTD2DInputs[0], ivec2(closestTri, 4), 0).xyz;
        vec3 cC = texelFetch(sTD2DInputs[0], ivec2(closestTri, 5), 0).xyz;
        vec3 col = w * cA + closestV * cB + closestU * cC;
        fragColor = TDOutputSwizzle(vec4(col, 1.0));
    } else {
        fragColor = vec4(0.0);
    }
}
