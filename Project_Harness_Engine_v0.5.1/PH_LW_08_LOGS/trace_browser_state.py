import sys,time,unittest,json
def trace(frame,event,arg):
    if frame.f_code.co_name != 'test_ui_upload_preview_duplicate_replace_and_no_documentation': return None
    if event=='line':
        print('BROWSER_LINE',frame.f_lineno,round(time.monotonic(),2),flush=True)
        if frame.f_lineno==339:
            print('BEFORE_BROWSER_CLOSE',json.dumps({'errors':frame.f_locals.get('errors'),'requests':frame.f_locals.get('requests'),'exception':str(sys.exception())},ensure_ascii=False),flush=True)
    return trace
sys.settrace(trace)
unittest.main(module=None,argv=['unittest','-v','tests.test_ph_lw_04_05_acceptance.BrowserImportAcceptance.test_ui_upload_preview_duplicate_replace_and_no_documentation'])
