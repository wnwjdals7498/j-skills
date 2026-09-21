using System.IO;
using UnityEditor;
using UnityEngine;

namespace AIVisual.Editor
{
    /// <summary>
    /// Draws the concept art on top of the Scene/Game view at a chosen opacity so the concept and
    /// the current render can be compared directly instead of side by side.
    ///
    /// 50% is the most useful setting: silhouettes and composition alignment become obvious.
    ///
    /// Open with: Tools/AI Visual/Concept Overlay
    /// </summary>
    public class ConceptOverlay : EditorWindow
    {
        private const string PrefOpacity = "AIVisual.ConceptOverlay.Opacity";
        private const string PrefTexturePath = "AIVisual.ConceptOverlay.TexturePath";
        private const string PrefEnabled = "AIVisual.ConceptOverlay.Enabled";
        private const string DefaultConceptPath = "Assets/../Docs/Visual/Reference/Concept_Master.png";

        private static Texture2D _overlay;
        private static float _opacity = 0.5f;
        private static bool _enabled;
        private static string _texturePath = "";

        [MenuItem("Tools/AI Visual/Concept Overlay")]
        public static void Open()
        {
            GetWindow<ConceptOverlay>("Concept Overlay").minSize = new Vector2(280, 160);
        }

        private void OnEnable()
        {
            _opacity = EditorPrefs.GetFloat(PrefOpacity, 0.5f);
            _enabled = EditorPrefs.GetBool(PrefEnabled, false);
            _texturePath = EditorPrefs.GetString(PrefTexturePath, DefaultConceptPath);
            LoadTexture();
            SceneView.duringSceneGui += OnSceneGUI;
        }

        private void OnDisable()
        {
            SceneView.duringSceneGui -= OnSceneGUI;
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Concept Overlay", EditorStyles.boldLabel);
            EditorGUILayout.Space();

            EditorGUI.BeginChangeCheck();
            _enabled = EditorGUILayout.Toggle("Enabled", _enabled);
            if (EditorGUI.EndChangeCheck())
            {
                EditorPrefs.SetBool(PrefEnabled, _enabled);
                SceneView.RepaintAll();
            }

            EditorGUILayout.BeginHorizontal();
            EditorGUILayout.LabelField("Concept image", GUILayout.Width(90));
            _texturePath = EditorGUILayout.TextField(_texturePath);
            if (GUILayout.Button("...", GUILayout.Width(28)))
            {
                string picked = EditorUtility.OpenFilePanel("Concept image", Application.dataPath, "png,jpg,jpeg");
                if (!string.IsNullOrEmpty(picked))
                {
                    _texturePath = picked;
                    EditorPrefs.SetString(PrefTexturePath, _texturePath);
                    LoadTexture();
                }
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space();

            EditorGUI.BeginChangeCheck();
            _opacity = EditorGUILayout.Slider("Opacity", _opacity, 0f, 1f);
            if (EditorGUI.EndChangeCheck())
            {
                EditorPrefs.SetFloat(PrefOpacity, _opacity);
                SceneView.RepaintAll();
            }

            // Preset buttons match the opacity steps the pipeline docs reference.
            EditorGUILayout.BeginHorizontal();
            foreach (float preset in new[] { 0f, 0.25f, 0.5f, 0.75f, 1f })
            {
                if (GUILayout.Button($"{preset * 100:0}%"))
                {
                    _opacity = preset;
                    EditorPrefs.SetFloat(PrefOpacity, _opacity);
                    SceneView.RepaintAll();
                }
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space();
            if (_overlay == null)
            {
                EditorGUILayout.HelpBox(
                    "Concept image not loaded. Set the path above.\n" +
                    "Default: Docs/Visual/Reference/Concept_Master.png",
                    MessageType.Warning);
            }
            else
            {
                EditorGUILayout.LabelField($"Loaded: {_overlay.width}x{_overlay.height}");
                EditorGUILayout.HelpBox(
                    "50% is the most useful setting for silhouette and composition alignment.",
                    MessageType.Info);
            }
        }

        private void LoadTexture()
        {
            _overlay = null;
            if (string.IsNullOrEmpty(_texturePath)) return;

            string path = _texturePath;
            if (!Path.IsPathRooted(path))
                path = Path.GetFullPath(Path.Combine(Application.dataPath, "..", path.Replace("Assets/../", "")));

            if (!File.Exists(path)) return;

            byte[] bytes = File.ReadAllBytes(path);
            Texture2D texture = new Texture2D(2, 2);
            if (texture.LoadImage(bytes)) _overlay = texture;
        }

        private static void OnSceneGUI(SceneView sceneView)
        {
            if (!_enabled || _overlay == null || _opacity <= 0f) return;

            Handles.BeginGUI();

            Rect view = sceneView.position;
            // Fit the concept image to the view while preserving aspect, so proportions stay comparable.
            float viewAspect = view.width / view.height;
            float imageAspect = (float)_overlay.width / _overlay.height;

            Rect target;
            if (imageAspect > viewAspect)
            {
                float height = view.width / imageAspect;
                target = new Rect(0, (view.height - height) * 0.5f, view.width, height);
            }
            else
            {
                float width = view.height * imageAspect;
                target = new Rect((view.width - width) * 0.5f, 0, width, view.height);
            }

            Color previous = GUI.color;
            GUI.color = new Color(1f, 1f, 1f, _opacity);
            GUI.DrawTexture(target, _overlay, ScaleMode.StretchToFill, true);
            GUI.color = previous;

            Handles.EndGUI();
        }
    }
}
