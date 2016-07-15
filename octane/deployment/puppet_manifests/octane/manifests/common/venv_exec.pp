define octane::common::venv_exec ($cmd = $title, $venv) {
  exec {
    provider => "shell",
    command => "$venv/activate && $cmd && deactivate"
  }
}