import subprocess


def test_schedule_readback_detects_cadence_drift():
    from data_library.scheduling import task_xml,status
    xml=task_xml().replace('PT2M','PT1M')
    def runner(*args,**kwargs): return subprocess.CompletedProcess(args,0,xml,'')
    assert status(runner=runner)['drift'] is True


def test_schedule_readback_detects_extra_action():
    from data_library.scheduling import task_xml,status
    xml=task_xml().replace('</Actions>','<Exec><Command>unexpected.exe</Command></Exec></Actions>')
    def runner(*args,**kwargs): return subprocess.CompletedProcess(args,0,xml,'')
    assert status(runner=runner)['drift'] is True
