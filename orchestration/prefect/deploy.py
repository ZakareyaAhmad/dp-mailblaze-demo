import os
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import IntervalSchedule
from datetime import timedelta

from flow import mailblaze_flow

if _name_ == "_main_":
    d = Deployment.build_from_flow(
        flow=mailblaze_flow,
        name="hourly",
        work_queue_name="default",
        schedule=IntervalSchedule(interval=timedelta(hours=1)),
    )
    d.apply()
    print("Deployment applied: hourly")