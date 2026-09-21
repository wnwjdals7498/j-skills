using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace AIVisual.Editor
{
    /// <summary>
    /// Checks the active scene against VISUAL_SPEC and ASSET_CATALOG and reports concrete,
    /// quantitative failures. Agents perform far better against numeric failure conditions than
    /// against prose rules, which is the whole point of this file.
    ///
    /// Spec is read as JSON (VISUAL_SPEC.json, generated alongside the authoritative YAML) because
    /// Unity ships no YAML parser. Regenerate the JSON whenever the YAML changes.
    ///
    /// Callable three ways:
    ///   - Menu:  Tools/AI Visual/Run Visual Linter
    ///   - CLI:   -executeMethod AIVisual.Editor.VisualLinter.RunFromCommandLine
    ///   - Code:  VisualLinter.Run()
    ///
    /// Rule ids follow "{area}.{item}" and are documented in
    /// references/guides/VISUAL_LINTER_SPEC.md. Adding a rule here is stronger than adding a
    /// sentence to a document: the linter does not forget.
    /// </summary>
    public static class VisualLinter
    {
        public const string SpecPath = "Docs/Visual/VISUAL_SPEC.json";
        public const string CatalogPath = "Docs/Visual/ASSET_CATALOG.json";
        public const string ResultPath = "Assets/VisualTests/lint_result.json";

        private static readonly string[] PrimitiveMeshNames =
        {
            "Cube", "Sphere", "Capsule", "Cylinder", "Plane", "Quad"
        };

        private static readonly string[] DefaultMaterialNames =
        {
            "Default-Material", "Sprite-Default", "Default-Line", "Default-Particle", "Lit"
        };

        // ─────────────────────────────────────────────────────────────
        // Entry points
        // ─────────────────────────────────────────────────────────────

        [MenuItem("Tools/AI Visual/Run Visual Linter")]
        public static void RunMenu()
        {
            LintResult result = Run();
            Debug.Log(result.ToConsoleReport());
        }

        /// <summary>Entry point for `unity -executeMethod`. Exits non-zero when errors are found.</summary>
        public static void RunFromCommandLine()
        {
            try
            {
                LintResult result = Run();
                Debug.Log(result.ToConsoleReport());
                EditorApplication.Exit(result.ErrorCount > 0 ? 1 : 0);
            }
            catch (Exception e)
            {
                Debug.LogError($"[VisualLinter] FAILED: {e}");
                EditorApplication.Exit(2);
            }
        }

        public static LintResult Run()
        {
            LintResult result = new LintResult
            {
                scene = SceneManager.GetActiveScene().name,
                ranAt = DateTime.Now.ToString("o")
            };

            VisualSpec spec = LoadSpec(result);
            if (spec == null) return Finish(result);

            HashSet<string> catalogPaths = LoadCatalogPaths(result);

            // Scene-level rules run once.
            CheckCamera(spec, result);
            CheckLighting(spec, result);
            CheckVolume(spec, result);

            // Object-level rules run per renderer.
            foreach (GameObject root in SceneManager.GetActiveScene().GetRootGameObjects())
            {
                foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
                {
                    CheckObject(transform, spec, catalogPaths, result);
                }
            }

            return Finish(result);
        }

        // ─────────────────────────────────────────────────────────────
        // Scene-level rules
        // ─────────────────────────────────────────────────────────────

        private static void CheckCamera(VisualSpec spec, LintResult result)
        {
            Camera camera = Camera.main;
            if (camera == null)
            {
                result.Error("camera.missing", "no MainCamera in scene", "");
                return;
            }

            bool wantOrthographic = spec.camera.projection == "orthographic";
            if (camera.orthographic != wantOrthographic)
            {
                result.Error("camera.projection",
                    $"expected {spec.camera.projection}, found {(camera.orthographic ? "orthographic" : "perspective")}",
                    camera.name);
            }

            if (wantOrthographic)
            {
                if (spec.camera.orthographic_size > 0f &&
                    Mathf.Abs(camera.orthographicSize - spec.camera.orthographic_size) > 0.01f)
                {
                    result.Error("camera.orthographic_size",
                        $"expected {spec.camera.orthographic_size}, found {camera.orthographicSize}", camera.name);
                }
            }
            else if (spec.camera.fov > 0f && Mathf.Abs(camera.fieldOfView - spec.camera.fov) > 0.5f)
            {
                result.Error("camera.fov",
                    $"expected {spec.camera.fov} (±0.5), found {camera.fieldOfView}", camera.name);
            }

            if (spec.camera.pitch > 0f)
            {
                float pitch = NormalizeAngle(camera.transform.eulerAngles.x);
                if (Mathf.Abs(pitch - spec.camera.pitch) > 1f)
                {
                    result.Error("camera.pitch",
                        $"expected {spec.camera.pitch} (±1), found {pitch:0.0}", camera.name);
                }
            }
        }

        private static void CheckLighting(VisualSpec spec, LintResult result)
        {
            Light directional = UnityEngine.Object
                .FindObjectsByType<Light>(FindObjectsSortMode.None)
                .FirstOrDefault(l => l.type == LightType.Directional && l.isActiveAndEnabled);

            if (directional == null)
            {
                result.Error("light.missing", "no active directional light in scene", "");
                return;
            }

            LightSpec want = spec.lighting?.main_light;
            if (want == null) return;

            if (want.rotation != null && want.rotation.Length >= 2)
            {
                Vector3 euler = directional.transform.eulerAngles;
                float x = NormalizeAngle(euler.x);
                float y = NormalizeAngle(euler.y);
                if (Mathf.Abs(Mathf.DeltaAngle(x, want.rotation[0])) > 2f ||
                    Mathf.Abs(Mathf.DeltaAngle(y, want.rotation[1])) > 2f)
                {
                    result.Error("light.rotation",
                        $"expected ({want.rotation[0]}, {want.rotation[1]}) ±2, found ({x:0.0}, {y:0.0})",
                        directional.name);
                }
            }

            if (want.intensity > 0f && Mathf.Abs(directional.intensity - want.intensity) > 0.1f)
            {
                result.Error("light.intensity",
                    $"expected {want.intensity} (±0.1), found {directional.intensity}", directional.name);
            }

            if (want.color_temperature > 0f && directional.useColorTemperature &&
                Mathf.Abs(directional.colorTemperature - want.color_temperature) > 100f)
            {
                result.Error("light.color_temperature",
                    $"expected {want.color_temperature}K (±100), found {directional.colorTemperature}K",
                    directional.name);
            }
        }

        private static void CheckVolume(VisualSpec spec, LintResult result)
        {
            // Volume lives in the render-pipeline assembly, which the linter must not hard-depend on.
            // Reflection keeps this file compiling in projects without URP/HDRP installed.
            Type volumeType = AppDomain.CurrentDomain.GetAssemblies()
                .Select(a => a.GetType("UnityEngine.Rendering.Volume"))
                .FirstOrDefault(t => t != null);

            if (volumeType == null) return;

            UnityEngine.Object[] volumes = UnityEngine.Object.FindObjectsByType(
                volumeType, FindObjectsSortMode.None);

            List<UnityEngine.Object> globals = new List<UnityEngine.Object>();
            foreach (UnityEngine.Object volume in volumes)
            {
                var isGlobal = volumeType.GetProperty("isGlobal")?.GetValue(volume) as bool?;
                if (isGlobal == true) globals.Add(volume);
            }

            if (globals.Count == 0)
            {
                result.Error("volume.missing", "no Global Volume in scene", "");
                return;
            }

            if (globals.Count > 1)
            {
                result.Error("volume.duplicate",
                    $"{globals.Count} global volumes found; expected exactly 1", "");
            }

            string expected = spec.postprocessing?.profile;
            if (string.IsNullOrEmpty(expected)) return;

            foreach (UnityEngine.Object volume in globals)
            {
                var profile = volumeType.GetProperty("sharedProfile")?.GetValue(volume) as UnityEngine.Object;
                string actual = profile != null ? profile.name : "<none>";
                if (actual != expected)
                {
                    result.Error("volume.profile",
                        $"expected profile '{expected}', found '{actual}'", volume.name);
                }
            }
        }

        // ─────────────────────────────────────────────────────────────
        // Object-level rules
        // ─────────────────────────────────────────────────────────────

        private static void CheckObject(Transform transform, VisualSpec spec,
            HashSet<string> catalogPaths, LintResult result)
        {
            GameObject go = transform.gameObject;
            string name = go.name;

            // MISSING_ objects are deliberate placeholders: report once, then exempt from the rest.
            if (HasPrefix(name, spec.linter?.exempt_prefixes, "MISSING_"))
            {
                result.Warn("missing.present", "unresolved visual asset", Path(transform));
                return;
            }

            bool exemptRoot = IsUnderExemptRoot(transform, spec.linter?.exempt_roots);
            bool blockoutPrefix = HasPrefix(name, spec.linter?.exempt_prefixes, "BLOCKOUT_");

            // Blockout naming must be consistent, otherwise the exemption becomes a loophole.
            if (exemptRoot && !blockoutPrefix && go.GetComponent<Renderer>() != null)
            {
                result.Error("blockout.naming",
                    "object under a blockout root is missing the BLOCKOUT_ prefix", Path(transform));
            }

            if (exemptRoot || blockoutPrefix) return;

            MeshFilter meshFilter = go.GetComponent<MeshFilter>();
            if (meshFilter != null && meshFilter.sharedMesh != null)
            {
                string meshName = meshFilter.sharedMesh.name;
                if (PrimitiveMeshNames.Contains(meshName))
                {
                    result.Error("primitive.outside_blockout",
                        $"{meshName} primitive used outside a blockout root", Path(transform));
                }

                if (catalogPaths.Count > 0)
                {
                    string assetPath = AssetDatabase.GetAssetPath(meshFilter.sharedMesh);
                    if (!string.IsNullOrEmpty(assetPath) &&
                        !assetPath.StartsWith("Library/") &&
                        !catalogPaths.Contains(assetPath) &&
                        !PrimitiveMeshNames.Contains(meshName))
                    {
                        result.Error("asset.not_in_catalog",
                            $"mesh '{assetPath}' is not in ASSET_CATALOG.json", Path(transform));
                    }
                }
            }

            Renderer renderer = go.GetComponent<Renderer>();
            if (renderer != null)
            {
                CheckMaterials(renderer, spec, result, Path(transform));
                CheckScale(transform, spec, result);
            }
        }

        private static void CheckMaterials(Renderer renderer, VisualSpec spec,
            LintResult result, string path)
        {
            foreach (Material material in renderer.sharedMaterials)
            {
                if (material == null)
                {
                    result.Error("material.null", "renderer has an empty material slot", path);
                    continue;
                }

                if (DefaultMaterialNames.Contains(material.name))
                {
                    result.Error("material.default",
                        $"Unity default material '{material.name}' in use", path);
                    continue;
                }

                if (spec.materials != null && !string.IsNullOrEmpty(spec.materials.master_shader))
                {
                    // Family membership is checked by name prefix so it works without custom metadata.
                    bool inFamily = spec.materials.families != null &&
                                    spec.materials.families.Any(f =>
                                        material.name.IndexOf(f, StringComparison.OrdinalIgnoreCase) >= 0);

                    if (!inFamily && material.name != spec.materials.master_shader)
                    {
                        result.Error("material.family",
                            $"'{material.name}' is not derived from an approved family " +
                            $"({string.Join(", ", spec.materials.families ?? new string[0])})", path);
                    }

                    if (material.HasProperty("_Metallic") &&
                        material.GetFloat("_Metallic") > spec.materials.metallic + 0.001f)
                    {
                        result.Error("material.metallic",
                            $"metallic {material.GetFloat("_Metallic"):0.00} exceeds max {spec.materials.metallic}",
                            path);
                    }

                    if (spec.materials.smoothness_max > 0f && material.HasProperty("_Smoothness") &&
                        material.GetFloat("_Smoothness") > spec.materials.smoothness_max + 0.001f)
                    {
                        result.Error("material.smoothness",
                            $"smoothness {material.GetFloat("_Smoothness"):0.00} exceeds max " +
                            $"{spec.materials.smoothness_max}", path);
                    }
                }

                CheckPaletteColor(material, spec, result, path);
            }
        }

        private static void CheckPaletteColor(Material material, VisualSpec spec,
            LintResult result, string path)
        {
            if (spec.palette == null || spec.palette.Length == 0) return;
            if (!material.HasProperty("_BaseColor") && !material.HasProperty("_Color")) return;

            Color color = material.HasProperty("_BaseColor")
                ? material.GetColor("_BaseColor")
                : material.GetColor("_Color");

            float tolerance = spec.linter?.color_delta_e_tolerance ?? 6f;
            foreach (string hex in spec.palette)
            {
                if (!ColorUtility.TryParseHtmlString(hex.StartsWith("#") ? hex : "#" + hex, out Color allowed))
                    continue;
                // Approximate perceptual distance; exact CIE ΔE is overkill for a gate check.
                float distance = Mathf.Sqrt(
                    Mathf.Pow((color.r - allowed.r) * 255f, 2) +
                    Mathf.Pow((color.g - allowed.g) * 255f, 2) +
                    Mathf.Pow((color.b - allowed.b) * 255f, 2)) / 4.4f;
                if (distance <= tolerance) return;
            }

            result.Error("material.color",
                $"'{material.name}' base color {ColorUtility.ToHtmlStringRGB(color)} is not in the palette",
                path);
        }

        private static void CheckScale(Transform transform, VisualSpec spec, LintResult result)
        {
            Vector3 scale = transform.localScale;
            bool forbidsNonUniform = spec.forbidden != null &&
                                     (spec.forbidden.Contains("non_uniform_scale") ||
                                      spec.forbidden.Contains("non_uniform_sprite_scale"));

            if (forbidsNonUniform &&
                (Mathf.Abs(scale.x - scale.y) > 0.001f || Mathf.Abs(scale.y - scale.z) > 0.001f))
            {
                result.Error("transform.non_uniform_scale",
                    $"scale ({scale.x:0.00}, {scale.y:0.00}, {scale.z:0.00}) is non-uniform",
                    Path(transform));
            }

            // 2D sizing must come from PPU and pivot, never from the transform.
            if (spec.profile == "2d" && transform.GetComponent<SpriteRenderer>() != null &&
                (Mathf.Abs(scale.x - 1f) > 0.001f || Mathf.Abs(scale.y - 1f) > 0.001f))
            {
                result.Error("sprite.transform_scale",
                    $"sprite scale ({scale.x:0.00}, {scale.y:0.00}) != 1; size sprites via PPU/pivot",
                    Path(transform));
            }
        }

        // ─────────────────────────────────────────────────────────────
        // Loading
        // ─────────────────────────────────────────────────────────────

        private static VisualSpec LoadSpec(LintResult result)
        {
            string path = ProjectFile(SpecPath);
            if (!File.Exists(path))
            {
                result.Error("spec.missing",
                    $"{SpecPath} not found; generate it from VISUAL_SPEC.yaml", "");
                return null;
            }

            try
            {
                VisualSpec spec = JsonUtility.FromJson<VisualSpec>(File.ReadAllText(path));
                if (spec == null)
                {
                    result.Error("spec.parse", $"{SpecPath} could not be parsed", "");
                    return null;
                }

                if (!spec.approved)
                {
                    result.Warn("spec.not_approved",
                        "VISUAL_SPEC is not approved yet; V1 must complete first", "");
                }

                return spec;
            }
            catch (Exception e)
            {
                result.Error("spec.parse", $"{SpecPath}: {e.Message}", "");
                return null;
            }
        }

        private static HashSet<string> LoadCatalogPaths(LintResult result)
        {
            HashSet<string> paths = new HashSet<string>();
            string path = ProjectFile(CatalogPath);
            if (!File.Exists(path))
            {
                result.Warn("catalog.missing",
                    $"{CatalogPath} not found; asset.not_in_catalog is disabled", "");
                return paths;
            }

            // Minimal extraction: pull every "path": "..." value rather than parsing the whole
            // document, so the catalog schema can grow without breaking the linter.
            foreach (string line in File.ReadAllLines(path))
            {
                int key = line.IndexOf("\"path\"", StringComparison.Ordinal);
                if (key < 0) continue;
                int first = line.IndexOf('"', line.IndexOf(':', key) + 1);
                int last = line.IndexOf('"', first + 1);
                if (first < 0 || last < 0) continue;
                string value = line.Substring(first + 1, last - first - 1);
                if (!string.IsNullOrEmpty(value)) paths.Add(value);
            }

            return paths;
        }

        // ─────────────────────────────────────────────────────────────
        // Helpers
        // ─────────────────────────────────────────────────────────────

        private static LintResult Finish(LintResult result)
        {
            string path = ProjectFile(ResultPath);
            string directory = System.IO.Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
            File.WriteAllText(path, JsonUtility.ToJson(result, true));
            AssetDatabase.Refresh();
            return result;
        }

        private static string ProjectFile(string relative)
        {
            return System.IO.Path.GetFullPath(
                System.IO.Path.Combine(Application.dataPath, "..", relative));
        }

        private static string Path(Transform transform)
        {
            StringBuilder builder = new StringBuilder(transform.name);
            Transform current = transform.parent;
            while (current != null)
            {
                builder.Insert(0, current.name + "/");
                current = current.parent;
            }
            return builder.ToString();
        }

        private static bool HasPrefix(string name, string[] configured, string fallback)
        {
            if (configured != null && configured.Length > 0)
                return configured.Any(p => p == fallback && name.StartsWith(p, StringComparison.Ordinal));
            return name.StartsWith(fallback, StringComparison.Ordinal);
        }

        private static bool IsUnderExemptRoot(Transform transform, string[] roots)
        {
            string[] effective = roots != null && roots.Length > 0
                ? roots
                : new[] { "Blockout", "EditorOnly" };

            Transform current = transform;
            while (current != null)
            {
                if (effective.Contains(current.name)) return true;
                current = current.parent;
            }
            return false;
        }

        private static float NormalizeAngle(float angle)
        {
            angle %= 360f;
            if (angle > 180f) angle -= 360f;
            return angle;
        }

        // ─────────────────────────────────────────────────────────────
        // Serializable models
        // ─────────────────────────────────────────────────────────────

        [Serializable]
        public class VisualSpec
        {
            public string profile;
            public bool approved;
            public CameraSpec camera = new CameraSpec();
            public LightingSpec lighting = new LightingSpec();
            public MaterialsSpec materials = new MaterialsSpec();
            public PostSpec postprocessing = new PostSpec();
            public string[] palette;
            public string[] forbidden;
            public LinterSpec linter = new LinterSpec();
        }

        [Serializable] public class CameraSpec
        {
            public string projection = "perspective";
            public float fov;
            public float orthographic_size;
            public float pitch;
        }

        [Serializable] public class LightingSpec { public LightSpec main_light; }

        [Serializable] public class LightSpec
        {
            public float[] rotation;
            public float color_temperature;
            public float intensity;
        }

        [Serializable] public class MaterialsSpec
        {
            public string master_shader;
            public string[] families;
            public float metallic;
            public float smoothness_max;
        }

        [Serializable] public class PostSpec { public string profile; }

        [Serializable] public class LinterSpec
        {
            public string[] exempt_roots;
            public string[] exempt_prefixes;
            public float color_delta_e_tolerance = 6f;
        }

        [Serializable]
        public class LintResult
        {
            public string scene;
            public string ranAt;
            public List<Finding> findings = new List<Finding>();

            public int ErrorCount => findings.Count(f => f.severity == "error");
            public int WarningCount => findings.Count(f => f.severity == "warning");

            public void Error(string rule, string message, string target) =>
                findings.Add(new Finding { severity = "error", rule = rule, message = message, target = target });

            public void Warn(string rule, string message, string target) =>
                findings.Add(new Finding { severity = "warning", rule = rule, message = message, target = target });

            public string ToConsoleReport()
            {
                StringBuilder builder = new StringBuilder();
                builder.AppendLine($"Scene Check — {scene}");
                builder.AppendLine("────────────────────────────────────────");

                if (findings.Count == 0) builder.AppendLine("no findings");

                foreach (Finding finding in findings.OrderBy(f => f.severity))
                {
                    string mark = finding.severity == "error" ? "ERROR  " : "WARN   ";
                    builder.AppendLine($"{mark} {finding.rule,-32} {finding.message}" +
                                       (string.IsNullOrEmpty(finding.target) ? "" : $"  [{finding.target}]"));
                }

                builder.AppendLine();
                builder.AppendLine($"Errors: {ErrorCount}   Warnings: {WarningCount}");
                builder.AppendLine($"Result written to {ResultPath}");
                return builder.ToString();
            }
        }

        [Serializable]
        public class Finding
        {
            public string severity;
            public string rule;
            public string message;
            public string target;
        }
    }
}
