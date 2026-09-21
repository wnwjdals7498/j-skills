using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace AIVisual.Editor
{
    /// <summary>
    /// Captures the Game View at a fixed resolution so an agent can inspect the actual render
    /// instead of assuming the change worked. Screenshots are the evidence required by VISUAL_DOD.
    ///
    /// Callable three ways:
    ///   - Menu:  Tools/AI Visual/Capture Game View
    ///   - CLI:   -executeMethod AIVisual.Editor.GameViewCapture.CaptureFromCommandLine
    ///   - Code:  GameViewCapture.Capture(width, height, path)
    ///
    /// CLI arguments (all optional):
    ///   -captureWidth 1920  -captureHeight 1080  -capturePath Assets/VisualTests/Screenshots/x.png
    /// </summary>
    public static class GameViewCapture
    {
        public const string DefaultDirectory = "Assets/VisualTests/Screenshots";
        public const int DefaultWidth = 1920;
        public const int DefaultHeight = 1080;

        [MenuItem("Tools/AI Visual/Capture Game View")]
        public static void CaptureMenu()
        {
            string path = Capture(DefaultWidth, DefaultHeight, null);
            Debug.Log($"[GameViewCapture] saved: {path}");
        }

        /// <summary>Entry point for `unity -executeMethod`. Reads capture settings from CLI args.</summary>
        public static void CaptureFromCommandLine()
        {
            int width = ArgInt("-captureWidth", DefaultWidth);
            int height = ArgInt("-captureHeight", DefaultHeight);
            string path = ArgString("-capturePath", null);

            try
            {
                string saved = Capture(width, height, path);
                Debug.Log($"[GameViewCapture] saved: {saved}");
            }
            catch (Exception e)
            {
                // Surface the failure instead of exiting 0 with no screenshot.
                Debug.LogError($"[GameViewCapture] FAILED: {e}");
                EditorApplication.Exit(1);
            }
        }

        /// <summary>
        /// Renders the active scene through the main camera into a RenderTexture and writes a PNG.
        /// Uses an offscreen render rather than the Game View window so it works in batch mode.
        /// </summary>
        /// <returns>The path the PNG was written to.</returns>
        public static string Capture(int width, int height, string path)
        {
            if (width <= 0 || height <= 0)
                throw new ArgumentException($"invalid capture size {width}x{height}");

            Camera camera = Camera.main;
            if (camera == null)
            {
                // Fall back to any enabled camera so a scene without a MainCamera tag still captures.
                Camera[] cameras = UnityEngine.Object.FindObjectsByType<Camera>(FindObjectsSortMode.None);
                foreach (Camera c in cameras)
                {
                    if (c.isActiveAndEnabled)
                    {
                        camera = c;
                        break;
                    }
                }
            }

            if (camera == null)
                throw new InvalidOperationException("no active camera in scene; cannot capture");

            if (string.IsNullOrEmpty(path))
            {
                string scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene().name;
                if (string.IsNullOrEmpty(scene)) scene = "untitled";
                path = Path.Combine(DefaultDirectory,
                    $"capture_{scene}_{DateTime.Now:yyyyMMdd_HHmm}.png");
            }

            string directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);

            RenderTexture rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32);
            rt.antiAliasing = 1;

            RenderTexture previousActive = RenderTexture.active;
            RenderTexture previousTarget = camera.targetTexture;

            Texture2D image = new Texture2D(width, height, TextureFormat.RGB24, false);

            try
            {
                camera.targetTexture = rt;
                camera.Render();

                RenderTexture.active = rt;
                image.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                image.Apply();

                File.WriteAllBytes(path, image.EncodeToPNG());
            }
            finally
            {
                camera.targetTexture = previousTarget;
                RenderTexture.active = previousActive;
                UnityEngine.Object.DestroyImmediate(image);
                rt.Release();
                UnityEngine.Object.DestroyImmediate(rt);
            }

            AssetDatabase.Refresh();
            return path;
        }

        private static string ArgString(string name, string fallback)
        {
            string[] args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
            {
                if (args[i] == name) return args[i + 1];
            }
            return fallback;
        }

        private static int ArgInt(string name, int fallback)
        {
            string raw = ArgString(name, null);
            return int.TryParse(raw, out int value) ? value : fallback;
        }
    }
}
