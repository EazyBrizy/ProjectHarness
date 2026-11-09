import sys,time,unittest,faulthandler
faulthandler.dump_traceback_later(45,repeat=True)
def trace(frame,event,arg):
    if frame.f_code.co_name=='test_ui_upload_preview_duplicate_replace_and_no_documentation' and event=='line':
        print('BROWSER_LINE',frame.f_lineno,round(time.monotonic(),2),flush=True)
    return trace
sys.settrace(trace)
unittest.main(module=None,argv=['unittest','-v','tests.test_ph_lw_04_05_acceptance.BrowserImportAcceptance.test_ui_upload_preview_duplicate_replace_and_no_documentation'])
