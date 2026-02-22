from datetime import timedelta

from flow import mailblaze_flow
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import IntervalSchedule

if __name__ == "__main__":
    d = Deployment.build_from_flow(
        flow=mailblaze_flow,
        name="hourly",
        work_queue_name="default",
        schedule=IntervalSchedule(interval=timedelta(hours=1)),
    )
    d.apply()
    print("Deployment applied: hourly")
