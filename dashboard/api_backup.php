<?php
// QENEX Real-time Stats API
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// First check if stats collector has recent data
$stats_file = '/opt/qenex-os/data/stats.json';
if (file_exists($stats_file)) {
    $stats_data = json_decode(file_get_contents($stats_file), true);
    // Use collector data if it's less than 10 seconds old
    if (isset($stats_data['timestamp']) && (time() - $stats_data['timestamp']) < 10) {
        echo json_encode($stats_data);
        exit;
    }
}

// Otherwise collect stats directly
// Get real system uptime
$uptime_seconds = shell_exec("cat /proc/uptime | awk '{print $1}'");
$uptime_hours = round($uptime_seconds / 3600, 1);

// Get load average
$load = sys_getloadavg();

// Get memory usage
$mem_total = shell_exec("grep MemTotal /proc/meminfo | awk '{print $2}'");
$mem_free = shell_exec("grep MemAvailable /proc/meminfo | awk '{print $2}'");
$mem_used_percent = round((1 - ($mem_free / $mem_total)) * 100, 1);

// Get CPU usage
$cpu_usage = shell_exec("top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\([0-9.]*\)%* id.*/\1/' | awk '{print 100 - $1}'");

// Count QENEX processes
$qenex_processes = shell_exec("ps aux | grep -E '[q]enex|[c]icd|[g]itops|[a]i_engine' | wc -l");

// Get real QENEX pipeline data
$pipelines = 0;
$success_rate = 0;
$deployments = 0;
$builds_today = 0;

// Check multiple log sources
$log_files = [
    '/opt/qenex-os/logs/cicd.log',
    '/opt/qenex-os/logs/pipeline.log',
    '/opt/qenex-os/logs/gitops.log'
];

foreach ($log_files as $log_file) {
    if (file_exists($log_file)) {
        $logs = file_get_contents($log_file);
        
        // Count pipeline executions
        $pipelines += substr_count($logs, '[Pipeline Started]');
        $pipelines += substr_count($logs, 'Pipeline execution started');
        
        // Count successful completions
        $success_count = substr_count($logs, '[Pipeline Success]');
        $success_count += substr_count($logs, 'Pipeline completed successfully');
        
        // Count total completions
        $total_count = substr_count($logs, '[Pipeline Completed]');
        $total_count += substr_count($logs, 'Pipeline execution completed');
        
        if ($total_count > 0) {
            $success_rate = round(($success_count / $total_count) * 100, 1);
        }
        
        // Count deployments
        $deployments += substr_count($logs, '[Deployment Success]');
        $deployments += substr_count($logs, 'Deployment completed');
        
        // Count today's builds
        $today = date('Y-m-d');
        $lines = explode("\n", $logs);
        foreach ($lines as $line) {
            if (strpos($line, $today) !== false && stripos($line, 'build') !== false) {
                $builds_today++;
            }
        }
    }
}

// If no pipeline data from logs, check running services
if ($pipelines == 0) {
    $running = shell_exec("ps aux | grep -E 'pipeline|cicd' | grep -v grep | wc -l");
    $pipelines = intval($running);
}

// Get disk usage
$disk_usage = shell_exec("df -h / | awk 'NR==2 {print $5}' | sed 's/%//'");

// Get network connections
$connections = shell_exec("ss -tun | wc -l");

echo json_encode([
    'uptime_hours' => $uptime_hours,
    'pipelines' => $pipelines,
    'success_rate' => $success_rate,
    'deployments' => $deployments,
    'builds_today' => $builds_today,
    'load_average' => round($load[0], 2),
    'memory_usage' => $mem_used_percent,
    'cpu_percent' => round(floatval($cpu_usage), 1),
    'disk_usage' => intval($disk_usage),
    'network_connections' => intval($connections),
    'qenex_processes' => intval($qenex_processes),
    'timestamp' => time(),
    'datetime' => date('Y-m-d H:i:s')
]);
?>