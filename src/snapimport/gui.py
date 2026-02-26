import asyncio
import os
import shutil
from pathlib import Path
from nicegui import ui, app, run
from .config import Config, load_config, save_config, config_exists
from .sd import detect_sds, list_all_volumes, has_camera_files
from .rename import find_files, get_renames, rename_files_in_folder
from .core import log_seen_files


@ui.page('/')
def start_gui():
    ui.dark_mode().enable()

    with ui.header():
        ui.label('SnapImport ✨').classes('text-2xl font-bold text-purple-400')
        ui.label('SD card to dated perfection in one drag').classes('text-sm text-gray-400')

    with ui.stepper() as stepper:
        with ui.step('Setup'):
            setup_step()

        with ui.step('Detect SD'):
            detect_sd_step()

        with ui.step('Dry Run / Import'):
            dry_run_import_step()

        with ui.step('Rename Folder'):
            rename_folder_step()


def setup_step():
    if config_exists():
        config = load_config()
        photos_input = ui.input('Photos Directory', value=str(config.photos_dir))
        photos_input.set_enabled(False)
        logs_input = ui.input('Logs Directory', value=str(config.logs_dir))
        logs_input.set_enabled(False)
        edit_toggle = ui.switch('Edit')
        def toggle_edit():
            enabled = edit_toggle.value
            photos_input.set_enabled(enabled)
            logs_input.set_enabled(enabled)
        edit_toggle.on_value_change(toggle_edit)
    else:
        photos_input = ui.input('Photos Directory')
        logs_input = ui.input('Logs Directory')

    async def pick_photos():
        await open_file_dialog(photos_input)

    def save_config_action():
        try:
            save_config(Config(photos_dir=str(Path(photos_input.value).expanduser()), logs_dir=str(Path(logs_input.value).expanduser())))
            ui.notify('Config saved ✔', type='positive')
        except Exception as e:
            ui.notify(str(e), type='negative')

    ui.button('Save Config', on_click=save_config_action)
    ui.button('Pick Photos Folder', on_click=lambda: asyncio.create_task(open_file_dialog(photos_input)))
    ui.button('Pick Logs Folder', on_click=lambda: asyncio.create_task(open_file_dialog(logs_input)))

sd_table = None
sd_spinner = None
sd_radio = None

def detect_sd_step():
    global sd_table, sd_spinner, sd_radio
    ui.button('Scan for SD cards', on_click=scan_sds)
    sd_spinner = ui.spinner('dots').set_visibility(False)
    sd_table = ui.table(
        columns=[
            {'name': 'volume', 'label': 'Volume path', 'field': 'volume'},
            {'name': 'has', 'label': 'Has camera files', 'field': 'has'}
        ],
        rows=[]
    )
    ui.label('Select SD card')
    sd_radio = ui.radio(options=[]).set_visibility(False)

async def scan_sds():
    sd_spinner.set_visibility(True)
    try:
        sds = await run.io_bound(detect_sds)
        volumes = await run.io_bound(list_all_volumes)
        rows = []
        options = []
        for vol_path, _ in volumes:
            has = await run.io_bound(has_camera_files, vol_path)
            rows.append({'volume': vol_path, 'has': '✅' if has else '❌'})
            if has:
                options.append(vol_path)
        sd_table.rows = rows
        if options:
            sd_radio.options = options
            sd_radio.set_visibility(True)
        else:
            sd_radio.set_visibility(False)
    except Exception as e:
        ui.notify(str(e), type='negative')
    finally:
        sd_spinner.set_visibility(False)

dry_run_button = None
import_button = None
dry_run_table = None
progress_card = None
progress_bar = None
progress_label = None

def dry_run_import_step():
    global dry_run_button, import_button, dry_run_table, progress_card, progress_bar, progress_label
    dry_run_button = ui.button('Dry Run', on_click=dry_run)
    import_button = ui.button('Import', on_click=do_import)
    dry_run_table = ui.table(
        columns=[
            {'name': 'orig', 'label': 'Original filename', 'field': 'orig'},
            {'name': 'new', 'label': 'New filename', 'field': 'new'}
        ],
        rows=[]
    )
    progress_card = ui.card()
    progress_card.set_visibility(False)
    with progress_card:
        progress_bar = ui.linear_progress()
        progress_label = ui.label('')

async def dry_run():
    dry_run_button.disable()
    try:
        sd_path = sd_radio.value if sd_radio.value else None
        if not sd_path:
            ui.notify('No SD selected', type='negative')
            return
        config = load_config()
        files = await run.io_bound(find_files, sd_path)
        renames = await run.io_bound(get_renames, files, config.photos_dir)
        rows = [{'orig': Path(orig).name, 'new': Path(new).name} for orig, new in renames.items()]
        dry_run_table.rows = rows
    except Exception as e:
        ui.notify(str(e), type='negative')
    finally:
        dry_run_button.enable()

async def do_import():
    import_button.disable()
    dry_run_button.disable()
    progress_card.set_visibility(True)
    try:
        sd_path = sd_radio.value
        if not sd_path:
            ui.notify('No SD selected', type='negative')
            return
        config = load_config()
        files = await run.io_bound(find_files, sd_path)
        total_files = len(files)
        total_bytes = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
        state = {'copied': 0, 'current_file': 0}
        def update_progress():
            progress_bar.value = state['copied'] / total_bytes if total_bytes > 0 else 1
            progress_label.text = f"Copying {state['current_file']} of {total_files} files"
        timer = ui.timer(0.2, update_progress)
        # Copy files
        dest_dir = Path(config.photos_dir)
        for i, src in enumerate(files):
            state['current_file'] = i + 1
            dest = dest_dir / Path(src).name
            await run.io_bound(shutil.copy2, src, dest)
            state['copied'] += os.path.getsize(src)
        timer.deactivate()
        progress_bar.value = 1
        # Rename
        copied_files = [str(dest_dir / Path(f).name) for f in files]
        renames = await run.io_bound(get_renames, copied_files, config.photos_dir)
        await run.io_bound(rename_files_in_folder, dest_dir)
        # Log
        await run.io_bound(log_seen_files, config, files)
        ui.notify(f'Done! {len(files)} files imported.', type='positive')
    except PermissionError:
        ui.notify('Some files are root-owned. Run `sudo chown -R $USER <photos_dir>` in Terminal and try again.', type='negative')
    except Exception as e:
        ui.notify(str(e), type='negative')
    finally:
        progress_card.set_visibility(False)
        import_button.enable()
        dry_run_button.enable()

rename_path_input = None
rename_button = None

def rename_folder_step():
    global rename_path_input, rename_button
    rename_path_input = ui.input('Folder to Rename')
    
    async def pick_rename():
        await open_file_dialog(rename_path_input)
    
    ui.button('Pick Folder', on_click=pick_rename)
    rename_button = ui.button('Rename', on_click=do_rename)

async def do_rename():
    rename_button.disable()
    try:
        folder_str = rename_path_input.value
        if not folder_str:
            ui.notify('No folder selected', type='negative')
            return
        folder = Path(folder_str).expanduser()
        renames = await run.io_bound(rename_files_in_folder, folder)
        ui.notify(f'Renamed {len(renames)} files.', type='positive')
    except Exception as e:
        ui.notify(str(e), type='negative')
    finally:
        rename_button.enable()


async def open_file_dialog(input_field):
    if app.native.main_window is None:
        ui.notify('File dialog not available in this mode.', type='negative')
    else:
        try:
            import webview
            paths = await app.native.main_window.create_file_dialog(webview.FOLDER_DIALOG)
            if paths:
                input_field.value = paths[0]
        except:
            ui.notify('File dialog not available in this mode.', type='negative')
