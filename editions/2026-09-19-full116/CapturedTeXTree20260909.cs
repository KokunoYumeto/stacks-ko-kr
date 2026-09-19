using System;
using System.IO;
using System.Runtime.InteropServices;
using System.ComponentModel;
using System.Diagnostics;
using System.Threading;

public sealed class CapturedTeXTree20260909 : IDisposable {
    [StructLayout(LayoutKind.Sequential)] struct SI {
        public uint cb; public IntPtr reserved, desktop, title;
        public uint x,y,xSize,ySize,xChars,yChars,fill,flags;
        public ushort show,cb2; public IntPtr reserved2,input,output,error;
    }
    [StructLayout(LayoutKind.Sequential)] struct PI { public IntPtr process,thread; public uint pid,tid; }
    [StructLayout(LayoutKind.Sequential)] struct BasicLimits {
        public long processTime,jobTime; public uint flags;
        public UIntPtr minWs,maxWs; public uint activeLimit; public UIntPtr affinity;
        public uint priority,scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct IO { public ulong rOps,wOps,oOps,rBytes,wBytes,oBytes; }
    [StructLayout(LayoutKind.Sequential)] struct Limits {
        public BasicLimits basic; public IO io; public UIntPtr processMem,jobMem,peakProcess,peakJob;
    }
    [StructLayout(LayoutKind.Sequential)] struct Accounting {
        public long user,kernel,periodUser,periodKernel; public uint faults,total,active,terminated;
    }
    [DllImport("kernel32", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr attrs,string name);
    [DllImport("kernel32", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int cls,ref Limits data,uint size);
    [DllImport("kernel32", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int cls,out Accounting data,uint size,IntPtr ret);
    [DllImport("kernel32", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateProcess(string exe,System.Text.StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref SI si,out PI pi);
    [DllImport("kernel32", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
    [DllImport("kernel32", SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32", SetLastError=true)] static extern bool SetHandleInformation(IntPtr h,uint mask,uint flags);
    [DllImport("kernel32", SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
    [DllImport("kernel32", SetLastError=true)] static extern bool TerminateJobObject(IntPtr job,uint code);
    [DllImport("kernel32", SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
    [DllImport("kernel32", SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint milliseconds);
    [DllImport("kernel32")] static extern bool CloseHandle(IntPtr h);
    IntPtr job,process; FileStream stdout,stderr;
    public uint Id {get;private set;}
    static void Check(bool ok) { if (!ok) throw new Win32Exception(Marshal.GetLastWin32Error()); }
    public CapturedTeXTree20260909(string exe,string arguments,string cwd,string outPath,string errPath) {
        PI pi=new PI(); bool assigned=false;
        try {
            job=CreateJobObject(IntPtr.Zero,null); Check(job!=IntPtr.Zero);
            var limits=new Limits(); limits.basic.flags=0x2000; // Kill this captured tree if the owner dies.
            Check(SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf<Limits>()));
            stdout=new FileStream(outPath,FileMode.CreateNew,FileAccess.Write,FileShare.Read);
            stderr=new FileStream(errPath,FileMode.CreateNew,FileAccess.Write,FileShare.Read);
            var si=new SI(); si.cb=(uint)Marshal.SizeOf<SI>(); si.flags=0x100;
            si.output=stdout.SafeFileHandle.DangerousGetHandle(); si.error=stderr.SafeFileHandle.DangerousGetHandle();
            Check(SetHandleInformation(si.output,1,1)); Check(SetHandleInformation(si.error,1,1));
            Check(CreateProcess(exe,new System.Text.StringBuilder("\""+exe+"\" "+arguments),IntPtr.Zero,IntPtr.Zero,true,0x08000004,IntPtr.Zero,cwd,ref si,out pi));
            process=pi.process; Id=pi.pid;
            Check(AssignProcessToJobObject(job,process)); assigned=true;
            if(ResumeThread(pi.thread)==0xFFFFFFFF) throw new Win32Exception(Marshal.GetLastWin32Error());
        } catch {
            if(process!=IntPtr.Zero && !assigned) { Check(TerminateProcess(process,1)); WaitForSingleObject(process,0xFFFFFFFF); }
            Dispose(); throw;
        } finally { if(pi.thread!=IntPtr.Zero) CloseHandle(pi.thread); }
    }
    public uint ActiveProcesses { get { Accounting a; Check(QueryInformationJobObject(job,1,out a,(uint)Marshal.SizeOf<Accounting>(),IntPtr.Zero)); return a.active; } }
    public bool HasExited { get { return ActiveProcesses==0; } }
    public bool WaitForExit(int milliseconds) {
        var watch=Stopwatch.StartNew();
        while(!HasExited) { if(watch.ElapsedMilliseconds>=milliseconds) return false; Thread.Sleep(100); }
        return true;
    }
    public void WaitForExit() { while(!WaitForExit(15000)) {} }
    public uint ExitCode { get { uint value; Check(GetExitCodeProcess(process,out value)); return value; } }
    public void Dispose() {
        if(job!=IntPtr.Zero) {
            if(ActiveProcesses!=0) { Check(TerminateJobObject(job,1)); WaitForExit(); }
            CloseHandle(job); job=IntPtr.Zero;
        }
        if(process!=IntPtr.Zero) { CloseHandle(process); process=IntPtr.Zero; }
        if(stdout!=null) {stdout.Dispose();stdout=null;} if(stderr!=null) {stderr.Dispose();stderr=null;}
    }
}
