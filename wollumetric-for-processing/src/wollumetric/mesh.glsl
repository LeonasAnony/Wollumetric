#version 150

uniform vec2 screenSize;
uniform sampler2D mapData;
uniform mat4 invMatrix;
uniform vec4 fill;
uniform vec3 xyzMax;

uniform sampler2D voxelData;
uniform vec3 voxelRes;
uniform float slicesPerRow;
uniform vec2 atlasSize;
uniform vec3 meshMin;
uniform vec3 meshMax;

out vec4 fragColor;

vec4 mapColor;

vec3 pxLocation(void) {
  vec3 mapValue = vec3(mapColor.r, (mapColor.g + mapColor.a / 255.0), mapColor.b);
  vec4 pxLocation = vec4(mapValue * xyzMax.xyz, 1.);
  vec4 o = pxLocation * invMatrix;
  return o.xyz;
}

void main(void) {
  mapColor = texture(mapData, vec2(gl_FragCoord.x, screenSize.y - gl_FragCoord.y) / screenSize).rgba;
  if (mapColor != vec4(0., 0., 0., 0.)) {
    vec3 pos = pxLocation();

    // normalize position to [0, 1] within mesh AABB
    vec3 uv3 = (pos - meshMin) / (meshMax - meshMin);

    // bounds check
    if (uv3.x >= 0.0 && uv3.x <= 1.0 &&
        uv3.y >= 0.0 && uv3.y <= 1.0 &&
        uv3.z >= 0.0 && uv3.z <= 1.0) {

      // voxel coordinate (clamped)
      vec3 vc = clamp(floor(uv3 * (voxelRes - 1.0)), vec3(0.0), voxelRes - 1.0);

      // atlas lookup — z-slices are tiled in a 2-D grid
      float atlasCol = mod(vc.z, slicesPerRow);
      float atlasRow = floor(vc.z / slicesPerRow);

      vec2 atlasUV = vec2(
        (atlasCol * voxelRes.x + vc.x + 0.5) / atlasSize.x,
        (atlasRow * voxelRes.y + vc.y + 0.5) / atlasSize.y
      );

      float val = texture(voxelData, atlasUV).r;
      if (val > 0.5) {
        fragColor = vec4(fill.rgba);
        return;
      }
    }
  }
  discard;
}
