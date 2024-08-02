import subprocess
import datetime
import json
import asyncio
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table

# Create log files
timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
log_file = f"snapshot_log_{timestamp}.txt"
summary_file = f"snapshot_summary_{timestamp}.txt"
snap_rid_list_file = "snap_rid_list.txt"

console = Console()

# Prompt for the CHG number
chg_number = input("Enter the CHG number: ")
with open(log_file, "a") as f:
    f.write(f"CHG Number: {chg_number}\n\n")

# Define the number of days after which snapshots should be considered expired
expire_days = 3

# Create lists for successful and failed snapshots
successful_snapshots = []
failed_snapshots = []

def write_detailed_log(message):
    with open(log_file, "a") as f:
        f.write(f"{message}\n")

def write_snapshot_rid(snapshot_id):
    with open(snap_rid_list_file, "a") as f:
        f.write(f"{snapshot_id}\n")

async def run_az_command(command, max_retries=3, delay=5):
    for attempt in range(max_retries):
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return stdout.decode().strip(), stderr.decode().strip(), process.returncode
        else:
            write_detailed_log(f"Command failed (attempt {attempt + 1}): {command}")
            write_detailed_log(f"Error: {stderr.decode().strip()}")
            if attempt < max_retries - 1:
                write_detailed_log(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
    return "", stderr.decode().strip(), process.returncode

async def process_vm(resource_id, vm_name):
    write_detailed_log(f"Processing VM: {vm_name}")
    write_detailed_log(f"Resource ID: {resource_id}")

    # Get the subscription ID
    subscription_id = resource_id.split("/")[2]
    if not subscription_id:
        write_detailed_log(f"Failed to get subscription ID for VM: {vm_name}")
        failed_snapshots.append((vm_name, "Failed to get subscription ID"))
        return

    # Set the subscription ID
    _, stderr, returncode = await run_az_command(f"az account set --subscription {subscription_id}")
    if returncode != 0:
        write_detailed_log(f"Failed to set subscription ID: {subscription_id}")
        write_detailed_log(f"Error: {stderr}")
        failed_snapshots.append((vm_name, "Failed to set subscription ID"))
        return

    write_detailed_log(f"Subscription ID: {subscription_id}")

    # Get the disk ID of the VM's OS disk
    stdout, stderr, returncode = await run_az_command(f"az vm show --ids {resource_id} --query 'storageProfile.osDisk.managedDisk.id' -o tsv")
    if returncode != 0 or not stdout:
        write_detailed_log(f"Failed to get disk ID for VM: {vm_name}")
        write_detailed_log(f"Error: {stderr}")
        failed_snapshots.append((vm_name, "Failed to get disk ID"))
        return

    disk_id = stdout

    # Get the resource group name
    stdout, stderr, returncode = await run_az_command(f"az vm show --ids {resource_id} --query 'resourceGroup' -o tsv")
    if returncode != 0:
        write_detailed_log(f"Failed to get resource group for VM: {vm_name}")
        write_detailed_log(f"Error: {stderr}")
        failed_snapshots.append((vm_name, "Failed to get resource group"))
        return

    resource_group = stdout
    write_detailed_log(f"Resource group name: {resource_group}")

    # Create a snapshot
    snapshot_name = f"RH_{chg_number}_{vm_name}_{timestamp}"
    stdout, stderr, returncode = await run_az_command(f"az snapshot create --name {snapshot_name} --resource-group {resource_group} --source {disk_id}")
    if returncode != 0:
        write_detailed_log(f"Failed to create snapshot for VM: {vm_name}")
        write_detailed_log(f"Error: {stderr}")
        failed_snapshots.append((vm_name, "Failed to create snapshot"))
        return

    # Write snapshot details to log file
    write_detailed_log(f"Snapshot created: {snapshot_name}")
    write_detailed_log(json.dumps(json.loads(stdout), indent=2))

    # Extract snapshot ID and write to snap_rid_list.txt
    snapshot_data = json.loads(stdout)
    snapshot_id = snapshot_data.get('id')
    if snapshot_id:
        write_snapshot_rid(snapshot_id)
        write_detailed_log(f"Snapshot resource ID added to snap_rid_list.txt: {snapshot_id}")
    else:
        write_detailed_log(f"Warning: Could not extract snapshot resource ID for {snapshot_name}")

    # Check if the snapshot is expired
    snapshot_creation_time = datetime.datetime.strptime(snapshot_name.split("_")[-1], "%Y%m%d%H%M%S")
    if (datetime.datetime.now() - snapshot_creation_time).days > expire_days:
        write_detailed_log(f"Snapshot '{snapshot_name}' is expired, deleting...")
        await run_az_command(f"az snapshot delete --name {snapshot_name} --resource-group {resource_group} --yes")
        write_detailed_log(f"Deleted expired snapshot: {snapshot_name}")
    else:
        write_detailed_log(f"Snapshot created successfully for VM: {vm_name}")
        successful_snapshots.append((vm_name, snapshot_name))

def create_summary_table():
    table = Table(title="Snapshot Creation Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="magenta")

    table.add_row("Total VMs Processed", str(len(successful_snapshots) + len(failed_snapshots)))
    table.add_row("Successful Snapshots", str(len(successful_snapshots)))
    table.add_row("Failed Snapshots", str(len(failed_snapshots)))

    return table

async def main():
    try:
        with open("snapshot_vmlist.txt") as file:
            vm_list = [line.strip() for line in file if line.strip()]
            total_vms = len(vm_list)
    except FileNotFoundError:
        console.print("[bold red]Error: snapshot_vmlist.txt file not found.[/bold red]")
        return

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})")
    )
    task = progress.add_task("Snapshotting", total=total_vms)

    with Live(Panel(progress), refresh_per_second=4) as live:
        for line in vm_list:
            resource_id, vm_name = line.split()
            await process_vm(resource_id, vm_name)
            progress.update(task, advance=1)
            live.update(Panel(progress))

    # Display summary table
    summary_table = create_summary_table()
    console.print(summary_table)

    # Write summary to file
    with open(summary_file, "w") as f:
        f.write("Snapshot Creation Summary\n")
        f.write("========================\n\n")
        f.write(f"Total VMs processed: {total_vms}\n")
        f.write(f"Successful snapshots: {len(successful_snapshots)}\n")
        f.write(f"Failed snapshots: {len(failed_snapshots)}\n\n")

        f.write("Successful snapshots:\n")
        for vm, snapshot in successful_snapshots:
            f.write(f"- {vm}: {snapshot}\n")

        f.write("\nFailed snapshots:\n")
        for vm, error in failed_snapshots:
            f.write(f"- {vm}: {error}\n")

    console.print("\n[bold green]Snapshot creation and expiration process completed.[/bold green]")
    console.print(f"Detailed log: {log_file}")
    console.print(f"Summary: {summary_file}")
    console.print(f"Snapshot resource IDs: {snap_rid_list_file}")

if __name__ == "__main__":
    asyncio.run(main())