using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

internal static class Launcher
{
    private static readonly string Root = Path.Combine(Environment.GetEnvironmentVariable("LOCALAPPDATA") ??
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VHS Studio");
    private static readonly string Self = Assembly.GetExecutingAssembly().Location;
    private static readonly Encoding Utf8 = new UTF8Encoding(false, true);
    private static string app, runtime, runtimeHash, requirementsHash, downloadUrl;
    private static long downloadSize;
    private static bool interactive;
    private static ProgressDialog progress;

    internal static string Local(string german, string english)
    {
        return CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "de" ? german : english;
    }

    [STAThread]
    private static int Main(string[] args)
    {
        interactive = args.Length == 0;
        try
        {
            if (!Environment.Is64BitOperatingSystem)
                throw new PlatformNotSupportedException("VHS Studio requires 64-bit Windows.");
            ReadLock();
            bool applyUpdate = Array.IndexOf(args, "--apply-update") >= 0;
            if (!Ready(applyUpdate))
            {
                if (interactive) PrepareWithWindow(applyUpdate);
                else Prepare(applyUpdate);
            }
            string python = applyUpdate ? RuntimePython() : Path.Combine(app, ".venv", "Scripts", "python.exe");
            return LaunchApp(python, args);
        }
        catch (Exception ex)
        {
            string message = ex.GetBaseException().Message;
            Diagnostic(message);
            if (interactive) MessageBox.Show(message, "VHS Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static Stream Resource(string name)
    {
        Stream s = Assembly.GetExecutingAssembly().GetManifestResourceStream(name);
        if (s == null) throw new InvalidDataException("Missing launcher resource: " + name);
        return s;
    }

    private static void ReadLock()
    {
        Dictionary<string, object> data;
        using (StreamReader reader = new StreamReader(Resource("bootstrap-lock.json"), Utf8))
            data = new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(reader.ReadToEnd());
        var py = (Dictionary<string, object>)data["python"];
        string version = (string)data["version"];
        runtimeHash = (string)py["sha256"];
        requirementsHash = (string)data["requirements_sha256"];
        downloadUrl = (string)py["url"];
        downloadSize = Convert.ToInt64(py["size"], CultureInfo.InvariantCulture);
        if (!Regex.IsMatch(version, @"^\d{4}-\d{2}-\d{2}(-\d+)?$") ||
            !Regex.IsMatch(runtimeHash, "^[0-9a-f]{64}$") || !Regex.IsMatch(requirementsHash, "^[0-9a-f]{64}$") ||
            downloadSize <= 0 || !downloadUrl.StartsWith("https://github.com/astral-sh/python-build-standalone/releases/download/", StringComparison.Ordinal))
            throw new InvalidDataException("Invalid embedded runtime lock.");
        app = Path.Combine(Root, "cache", version + "-" + BuildInfo.PayloadHash.Substring(0, 20), "app");
        runtime = Path.Combine(Root, "runtime", runtimeHash);
    }

    private static string RuntimePython() { return Path.Combine(runtime, "python", "python.exe"); }

    private static bool Ready(bool update)
    {
        if (!File.Exists(RuntimePython()) || !File.Exists(Path.Combine(app, "app.py"))) return false;
        if (update) return true;
        string marker = Path.Combine(app, ".bootstrap-ready");
        return File.Exists(marker) && File.Exists(Path.Combine(app, ".venv", "Scripts", "python.exe")) &&
            File.ReadAllText(marker).Trim() == requirementsHash;
    }

    private static void Diagnostic(string text)
    {
        if (!interactive) { try { Console.Error.WriteLine(text); } catch (IOException) { } }
        try
        {
            Directory.CreateDirectory(Root);
            lock (LogSync) File.AppendAllText(Path.Combine(Root, "bootstrap.log"),
                DateTime.Now.ToString("s", CultureInfo.InvariantCulture) + " " + text + Environment.NewLine, Utf8);
        }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }
    private static readonly object LogSync = new object();

    private static void Status(string text, int percent)
    {
        if (progress != null) progress.SetStatus(text, percent);
        if (percent < 0 || percent == 0 || percent == 100) Diagnostic(text);
    }

    private static void PrepareWithWindow(bool applyUpdate)
    {
        Application.EnableVisualStyles();
        Exception error = null;
        using (var dialog = new ProgressDialog())
        {
            progress = dialog;
            dialog.Shown += delegate
            {
                Thread t = new Thread(delegate()
                {
                    try { Prepare(applyUpdate); } catch (Exception e) { error = e; }
                    dialog.BeginInvoke((Action)delegate { dialog.Close(); });
                });
                t.IsBackground = true;
                t.Start();
            };
            Application.Run(dialog);
            progress = null;
        }
        if (error != null) throw new InvalidOperationException("VHS Studio setup failed.", error);
    }

    private static void Prepare(bool update)
    {
        Directory.CreateDirectory(Root);
        string lockPath = Path.Combine(Root, "bootstrap.lock");
        using (FileStream setupLock = AcquireLock(lockPath))
        {
            if (Ready(update)) return;
            if (!File.Exists(Path.Combine(app, "app.py")))
            {
                Status(Local("Anwendung wird vorbereitet …", "Preparing the application …"), -1);
                StageDirectory(app, ExtractPayload);
            }
            if (!File.Exists(RuntimePython()))
            {
                Status(Local("Python wird vom Originalanbieter geladen …", "Downloading Python from its publisher …"), 0);
                StageDirectory(runtime, InstallRuntime);
            }
            if (!update && !Ready(false))
            {
                Status(Local("Python-Pakete werden eingerichtet …", "Installing Python packages …"), -1);
                RunSetup();
                if (!Ready(false)) throw new InvalidDataException("Package setup did not complete for this release.");
            }
        }
    }

    private static FileStream AcquireLock(string path)
    {
        bool announced = false;
        while (true)
        {
            try { return new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
            catch (IOException ex)
            {
                int code = ex.HResult & 0xffff;
                if (code != 32 && code != 33) throw;
                if (!announced) { Status(Local("Eine andere Installation wird abgeschlossen …", "Waiting for another installation to finish …"), -1); announced = true; }
                Thread.Sleep(250);
            }
        }
    }

    private static void StageDirectory(string destination, Action<string> populate)
    {
        string parent = Path.GetDirectoryName(destination);
        Directory.CreateDirectory(parent);
        string stage = Path.Combine(parent, ".install-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(stage);
        try
        {
            populate(stage);
            if (Directory.Exists(destination))
                Directory.Move(destination, destination + ".incomplete-" + Guid.NewGuid().ToString("N"));
            Directory.Move(stage, destination);
        }
        finally { if (Directory.Exists(stage)) Directory.Delete(stage, true); }
    }

    private static void ExtractPayload(string dir)
    {
        using (Stream s = Resource("payload.zip"))
        {
            if (Hash(s) != BuildInfo.PayloadHash) throw new InvalidDataException("Application source digest mismatch.");
        }
        using (Stream s = Resource("payload.zip"))
        using (ZipArchive archive = new ZipArchive(s, ZipArchiveMode.Read))
        {
            foreach (var entry in archive.Entries)
            {
                string path = SafePath(dir, entry.FullName);
                using (Stream input = entry.Open())
                using (FileStream output = new FileStream(path, FileMode.CreateNew, FileAccess.Write))
                    input.CopyTo(output);
            }
        }
        using (var s = File.OpenRead(Path.Combine(dir, "bootstrap-requirements.txt")))
            if (Hash(s) != requirementsHash) throw new InvalidDataException("Requirements digest mismatch.");
    }

    private static string Hash(Stream s)
    {
        using (var sha = SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
    }

    private static string SafePath(string root, string relative)
    {
        if (String.IsNullOrEmpty(relative) || relative.Contains("\\") || relative.Contains(":") || Path.IsPathRooted(relative))
            throw new InvalidDataException("Invalid archive path.");
        foreach (string part in relative.Split('/'))
            if (part.Length == 0 || part == "." || part == ".." || part.EndsWith(".", StringComparison.Ordinal) ||
                part.EndsWith(" ", StringComparison.Ordinal) || part.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 ||
                Regex.IsMatch(part, @"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)", RegexOptions.IgnoreCase))
                throw new InvalidDataException("Unsafe archive path: " + relative);
        string path = Path.GetFullPath(Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar)));
        if (!path.StartsWith(Path.GetFullPath(root) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Archive path outside destination.");
        return path;
    }

    private static void InstallRuntime(string dir)
    {
        string archive = Path.Combine(dir, "runtime.tar.gz");
        ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
        using (var response = OpenRuntimeDownload(downloadUrl))
        using (Stream input = response.GetResponseStream())
        using (var output = new FileStream(archive, FileMode.CreateNew, FileAccess.Write))
        {
            if (response.ResponseUri.Scheme != Uri.UriSchemeHttps) throw new InvalidDataException("Insecure runtime download.");
            byte[] buffer = new byte[128 * 1024];
            long count = 0;
            int n, last = 0;
            while ((n = input.Read(buffer, 0, buffer.Length)) > 0)
            {
                count += n;
                if (count > downloadSize) throw new InvalidDataException("Runtime exceeds expected size.");
                output.Write(buffer, 0, n);
                int pc = (int)(count * 100L / downloadSize);
                if (last != pc) { Status(Local("Python wird vom Originalanbieter geladen …", "Downloading Python from its publisher …"), pc); last = pc; }
            }
            if (count != downloadSize) throw new InvalidDataException("Incomplete runtime download.");
        }
        using (Stream s = File.OpenRead(archive))
        {
            if (Hash(s) != runtimeHash) throw new InvalidDataException("Runtime digest mismatch.");
            s.Position = 0;
            Status(Local("Python wird entpackt …", "Extracting Python …"), -1);
            using (var gz = new GZipStream(s, CompressionMode.Decompress, true)) ExtractTar(gz, dir);
        }
        File.Delete(archive);
        if (!File.Exists(Path.Combine(dir, "python", "python.exe"))) throw new InvalidDataException("Missing runtime executable.");
    }

    private static bool AllowedRuntimeUri(Uri uri)
    {
        return uri.IsAbsoluteUri && uri.Scheme == Uri.UriSchemeHttps && uri.IsDefaultPort &&
            uri.UserInfo.Length == 0 &&
            (uri.Host.Equals("github.com", StringComparison.OrdinalIgnoreCase) ||
             uri.Host.Equals("release-assets.githubusercontent.com", StringComparison.OrdinalIgnoreCase) ||
             uri.Host.Equals("objects.githubusercontent.com", StringComparison.OrdinalIgnoreCase));
    }

    private static HttpWebResponse OpenRuntimeDownload(string url)
    {
        Uri current = new Uri(url, UriKind.Absolute);
        for (int redirects = 0; redirects <= 8; redirects++)
        {
            if (!AllowedRuntimeUri(current)) throw new InvalidDataException("Untrusted runtime download address.");
            var request = (HttpWebRequest)WebRequest.Create(current);
            request.UserAgent = "VHS-Studio-Bootstrap";
            request.Timeout = 60000;
            request.ReadWriteTimeout = 60000;
            request.AllowAutoRedirect = false;
            var response = (HttpWebResponse)request.GetResponse();
            int status = (int)response.StatusCode;
            if (status == 301 || status == 302 || status == 303 || status == 307 || status == 308)
            {
                string location = response.Headers["Location"];
                response.Close();
                if (String.IsNullOrEmpty(location)) throw new InvalidDataException("Missing runtime redirect address.");
                current = new Uri(current, location);
                continue;
            }
            if (status == 200) return response;
            response.Close();
            throw new InvalidDataException("Unexpected runtime download response.");
        }
        throw new InvalidDataException("Too many runtime download redirects.");
    }

    private static string Field(byte[] header, int start, int length)
    {
        int n = 0; while (n < length && header[start + n] != 0) n++;
        return Utf8.GetString(header, start, n);
    }

    private static void CopyBytes(Stream source, Stream target, long count, byte[] buffer)
    {
        while (count > 0)
        {
            int n = source.Read(buffer, 0, (int)Math.Min(buffer.Length, count));
            if (n == 0) throw new EndOfStreamException("Incomplete TAR.");
            target.Write(buffer, 0, n);
            count -= n;
        }
    }

    private static Dictionary<string, string> Pax(byte[] bytes)
    {
        var values = new Dictionary<string, string>();
        int i = 0;
        while (i < bytes.Length)
        {
            int space = Array.IndexOf(bytes, (byte)' ', i);
            int length;
            if (space <= i || !int.TryParse(Encoding.ASCII.GetString(bytes, i, space - i), NumberStyles.None,
                CultureInfo.InvariantCulture, out length) || length > bytes.Length - i ||
                length <= space - i + 2 || bytes[i + length - 1] != 10)
                throw new InvalidDataException("Invalid TAR extended header.");
            string line = Utf8.GetString(bytes, space + 1, i + length - space - 2);
            int eq = line.IndexOf('=');
            if (eq <= 0) throw new InvalidDataException("Invalid TAR attribute.");
            values[line.Substring(0, eq)] = line.Substring(eq + 1);
            i += length;
        }
        return values;
    }

    private static void ExtractTar(Stream input, string dir)
    {
        byte[] header = new byte[512], buffer = new byte[65536];
        string nextPath = null, nextSize = null;
        long expanded = 0;
        while (true)
        {
            int count = 0;
            while (count < 512)
            {
                int n = input.Read(header, count, 512 - count);
                if (n == 0) throw new EndOfStreamException("Missing end of TAR.");
                count += n;
            }
            bool empty = true;
            for (int i = 0; i < 512; i++) if (header[i] != 0) { empty = false; break; }
            if (empty) return;
            long size = Convert.ToInt64(Field(header, 124, 12).Trim(' ', '\0'), 8);
            if (size < 0) throw new InvalidDataException("Invalid TAR size.");
            char type = (char)header[156];
            if (type == 'x' || type == 'L')
            {
                if (size > 1024 * 1024) throw new InvalidDataException("Oversized TAR header.");
                using (var meta = new MemoryStream())
                {
                    CopyBytes(input, meta, size, buffer);
                    if (type == 'L') nextPath = Utf8.GetString(meta.ToArray()).TrimEnd('\0');
                    else
                    {
                        var fields = Pax(meta.ToArray());
                        fields.TryGetValue("path", out nextPath);
                        fields.TryGetValue("size", out nextSize);
                    }
                }
            }
            else
            {
                string prefix = Field(header, 345, 155);
                string relative = nextPath ?? ((prefix.Length == 0 ? "" : prefix + "/") + Field(header, 0, 100));
                if (nextSize != null) size = long.Parse(nextSize, NumberStyles.None, CultureInfo.InvariantCulture);
                nextPath = null; nextSize = null;
                if (size < 0 || size > 2147483648L - expanded) throw new InvalidDataException("Oversized runtime archive.");
                expanded += size;
                if (type != '\0' && type != '0' && type != '5') throw new InvalidDataException("Unsupported TAR entry.");
                relative = relative.TrimEnd('/');
                if (relative != "python" && !relative.StartsWith("python/", StringComparison.Ordinal))
                    throw new InvalidDataException("Unexpected runtime archive root.");
                string dest = SafePath(dir, relative);
                if (type == '5') { if (size != 0) throw new InvalidDataException("Invalid TAR directory."); Directory.CreateDirectory(dest); }
                else
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(dest));
                    using (var f = new FileStream(dest, FileMode.CreateNew, FileAccess.Write))
                        CopyBytes(input, f, size, buffer);
                }
            }
            CopyBytes(input, Stream.Null, (512 - size % 512) % 512, buffer);
        }
    }

    private static ProcessStartInfo StartInfo(string exe, string[] args)
    {
        var info = new ProcessStartInfo(exe);
        var quoted = new List<string>();
        foreach (string a in args) quoted.Add(Quote(a));
        info.Arguments = string.Join(" ", quoted.ToArray());
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.EnvironmentVariables.Remove("PYTHONHOME");
        info.EnvironmentVariables.Remove("PYTHONPATH");
        info.EnvironmentVariables["PYTHONNOUSERSITE"] = "1";
        info.EnvironmentVariables["VHS_STUDIO_EXE"] = Self;
        info.EnvironmentVariables["VHS_STUDIO_APP_ROOT"] = app;
        info.EnvironmentVariables["VHS_STUDIO_BOOTSTRAP"] = "1";
        info.EnvironmentVariables["VHS_STUDIO_PYTHON_RUNTIME"] = RuntimePython();
        return info;
    }

    private static string Quote(string value)
    {
        var s = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in value)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') { s.Append('\\', slashes * 2 + 1); s.Append('"'); }
            else { s.Append('\\', slashes); s.Append(c); }
            slashes = 0;
        }
        return s.Append('\\', slashes * 2).Append('"').ToString();
    }

    private static void RunSetup()
    {
        var info = StartInfo(RuntimePython(), new string[] { "-I", Path.Combine(app, "bootstrap_setup.py") });
        info.WorkingDirectory = app;
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;
        using (var proc = new Process())
        {
            proc.StartInfo = info;
            DataReceivedEventHandler output = delegate(object sender, DataReceivedEventArgs e)
            {
                if (String.IsNullOrEmpty(e.Data)) return;
                Diagnostic(e.Data);
                if (progress != null) progress.SetStatus(e.Data, -1);
            };
            proc.OutputDataReceived += output;
            proc.ErrorDataReceived += output;
            proc.Start(); proc.BeginOutputReadLine(); proc.BeginErrorReadLine();
            proc.WaitForExit();
            if (proc.ExitCode != 0) throw new InvalidOperationException(Local("Paketinstallation fehlgeschlagen. Details: ", "Package installation failed. Details: ") + Path.Combine(Root, "bootstrap.log"));
        }
    }

    private static Thread Pump(Stream source, Stream target, bool closeTarget)
    {
        Thread t = new Thread(delegate()
        {
            try
            {
                byte[] b = new byte[16 * 1024];
                int n;
                while ((n = source.Read(b, 0, b.Length)) > 0) { target.Write(b, 0, n); target.Flush(); }
            }
            catch (IOException) { }
            catch (ObjectDisposedException) { }
            finally { if (closeTarget) try { target.Close(); } catch (IOException) { } }
        });
        t.IsBackground = true; t.Start(); return t;
    }

    private static int LaunchApp(string python, string[] args)
    {
        var a = new List<string>();
        a.Add(Path.Combine(app, "app.py")); a.AddRange(args);
        var info = StartInfo(python, a.ToArray());
        if (interactive)
        {
            using (var p = Process.Start(info)) { p.WaitForExit(); return p.ExitCode; }
        }
        info.RedirectStandardInput = true;
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;
        using (var p = Process.Start(info))
        {
            Pump(Console.OpenStandardInput(), p.StandardInput.BaseStream, true);
            Thread stdout = Pump(p.StandardOutput.BaseStream, Console.OpenStandardOutput(), false);
            Thread stderr = Pump(p.StandardError.BaseStream, Console.OpenStandardError(), false);
            p.WaitForExit();
            stdout.Join(); stderr.Join();
            return p.ExitCode;
        }
    }
}

internal sealed class ProgressDialog : Form
{
    private readonly Label status;
    private readonly ProgressBar bar;

    internal ProgressDialog()
    {
        Text = "VHS Studio";
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        ControlBox = false;
        ClientSize = new Size(460, 118);
        BackColor = Color.FromArgb(25, 36, 46);
        ForeColor = Color.White;
        Font = new Font("Segoe UI", 10);
        status = new Label { AutoEllipsis = true, Left = 22, Top = 22, Width = 416, Height = 34, Text = Launcher.Local("VHS Studio wird vorbereitet …", "Preparing VHS Studio …") };
        bar = new ProgressBar { Left = 22, Top = 69, Width = 416, Height = 11, Style = ProgressBarStyle.Marquee };
        Controls.Add(status); Controls.Add(bar);
    }

    internal void SetStatus(string message, int percent)
    {
        BeginInvoke((Action)delegate
        {
            status.Text = message;
            bar.Style = percent < 0 ? ProgressBarStyle.Marquee : ProgressBarStyle.Continuous;
            if (percent >= 0) bar.Value = percent;
        });
    }
}
