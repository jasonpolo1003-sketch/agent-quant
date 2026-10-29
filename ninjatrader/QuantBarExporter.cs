// QuantBarExporter: appends each completed 1-minute bar of its chart's instrument to a CSV
// that scripts/live_nt.py tails (quant_brain.live.ninjatrader.BarFileTail).
//
// File:   <Documents>\NinjaTrader 8\quant_bars\<Instrument FullName>_<yyyy-MM-dd>.csv
//         e.g. "MNQ 12-26_2026-10-29.csv"; one file per CT date of the bar start.
// Line:   date,time,open,high,low,close,volume   (bar START time in America/Chicago, prices
//         with a period decimal, e.g. 2026-10-29,08:30,21000.25,21001,20999.5,21000,812)
// Each line is written and flushed whole (File.AppendAllText opens, writes, closes), so the
// reader never sees half a bar unless it reads mid-write; it ignores a line without its
// newline. Historical bars are written too (ExportHistorical), so the runner can warm up its
// engine and build the sigma table from earlier days; reloading a chart rewrites them, and the
// reader drops the duplicates.
//
// Install (NT8): Tools > Import > NinjaScript is for zipped exports; for this source file,
// copy it to Documents\NinjaTrader 8\bin\Custom\Indicators\, open the NinjaScript Editor and
// compile (F5). Add "QuantBarExporter" to a 1-minute MNQ chart (Calculate = On bar close).
//
// NOT COMPILED HERE: written from the NinjaScript reference without an NT8 install, so check
// it compiles. Assumptions to confirm: Time[0] is the bar's END (close) time in the time zone
// set under Tools > Options > General (Core.Globals.GeneralOptions.TimeZoneInfo); bars with no
// trades are absent (as in the engine's data); OnBarUpdate with Calculate.OnBarClose runs once
// per completed bar, on the first tick of the next bar.
#region Using declarations
using System;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class QuantBarExporter : Indicator
    {
        private TimeZoneInfo central;
        private string folder;
        private DateTime lastStart = DateTime.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Appends each completed 1-minute bar (CT bar start, OHLC, volume) to a CSV.";
                Name = "QuantBarExporter";
                Calculate = Calculate.OnBarClose;
                IsOverlay = true;
                DisplayInDataBox = false;
                PaintPriceMarkers = false;
                IsSuspendedWhileInactive = false; // keep exporting when the chart is hidden
                ExportHistorical = true;
                FolderName = "quant_bars";
            }
            else if (State == State.DataLoaded)
            {
                if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 1)
                {
                    Log("QuantBarExporter needs a 1-minute chart; nothing will be exported.", LogLevel.Error);
                    return;
                }
                // "Central Standard Time" is the Windows ID for America/Chicago (CST and CDT).
                central = TimeZoneInfo.FindSystemTimeZoneById("Central Standard Time");
                folder = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, FolderName);
                Directory.CreateDirectory(folder);
            }
        }

        protected override void OnBarUpdate()
        {
            if (central == null || BarsInProgress != 0 || CurrentBar < 0)
                return;
            if (State == State.Historical && !ExportHistorical)
                return;
            DateTime end = DateTime.SpecifyKind(Time[0], DateTimeKind.Unspecified);
            DateTime endCt = TimeZoneInfo.ConvertTime(end, NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo, central);
            DateTime start = endCt.AddMinutes(-1);
            if (start <= lastStart)
                return; // never write the same bar twice from one load
            lastStart = start;
            CultureInfo inv = CultureInfo.InvariantCulture;
            string line = string.Join(",",
                start.ToString("yyyy-MM-dd", inv),
                start.ToString("HH:mm", inv),
                Open[0].ToString("R", inv),
                High[0].ToString("R", inv),
                Low[0].ToString("R", inv),
                Close[0].ToString("R", inv),
                Volume[0].ToString(inv)) + "\n";
            string file = Path.Combine(folder, Instrument.FullName + "_" + start.ToString("yyyy-MM-dd", inv) + ".csv");
            try
            {
                if (!File.Exists(file))
                    File.AppendAllText(file, "date,time,open,high,low,close,volume\n");
                File.AppendAllText(file, line);
            }
            catch (IOException e)
            {
                Log("QuantBarExporter could not write " + file + ": " + e.Message, LogLevel.Warning);
            }
        }

        [NinjaScriptProperty]
        [Display(Name = "Export historical bars", Order = 1, GroupName = "Parameters")]
        public bool ExportHistorical { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Folder (under Documents\\NinjaTrader 8)", Order = 2, GroupName = "Parameters")]
        public string FolderName { get; set; }
    }
}
