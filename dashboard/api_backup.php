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
// Get real system uptime - SECURITY FIX: Use file_get_contents instead of shell_exec
$uptime_line = file_get_contents('/proc/uptime');
$uptime_seconds = floatval(explode(' ', trim($uptime_line))[0]);
$uptime_hours = round($uptime_seconds / 3600, 1);

// Get load average
$load = sys_getloadavg();

// Get memory usage - SECURITY FIX: Parse /proc/meminfo directly
$meminfo = file_get_contents('/proc/meminfo');
preg_match('/MemTotal:\s+(\d+)/', $meminfo, $total_match);
preg_match('/MemAvailable:\s+(\d+)/', $meminfo, $avail_match);
$mem_total = intval($total_match[1]);
$mem_free = intval($avail_match[1]);
$mem_used_percent = round((1 - ($mem_free / $mem_total)) * 100, 1);

// Get CPU usage - SECURITY FIX: Use /proc/stat instead of shell commands
$stat_line = file_get_contents('/proc/stat');
if (preg_match('/cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/', $stat_line, $matches)) {
    $idle = intval($matches[4]);
    $total = array_sum(array_slice($matches, 1));
    $cpu_usage = round((1 - $idle / $total) * 100, 1);
} else {
    $cpu_usage = 0;
}

// Count QENEX processes - SECURITY FIX: Use /proc filesystem
$qenex_processes = 0;
try {
    $processes = glob('/proc/*/comm');
    foreach ($processes as $comm_file) {
        if (is_readable($comm_file)) {
            $comm = trim(file_get_contents($comm_file));
            if (preg_match('/qenex|cicd|gitops|ai_engine/i', $comm)) {
                $qenex_processes++;
            }
        }
    }
} catch (Exception $e) {
    $qenex_processes = 1;
}

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

// If no pipeline data from logs, check running services - SECURITY FIX
if ($pipelines == 0) {
    $running = 0;
    try {
        $processes = glob('/proc/*/comm');
        foreach ($processes as $comm_file) {
            if (is_readable($comm_file)) {
                $comm = trim(file_get_contents($comm_file));
                if (preg_match('/pipeline|cicd/i', $comm)) {
                    $running++;
                }
            }
        }
    } catch (Exception $e) {
        $running = 0;
    }
    $pipelines = $running;
}

// Get disk usage - SECURITY FIX: Use disk_free_space function
$total_space = disk_total_space('/');
$free_space = disk_free_space('/');
$disk_usage = round((($total_space - $free_space) / $total_space) * 100, 0);

// Get network connections - SECURITY FIX: Use /proc/net/tcp
$connections = 0;
try {
    $tcp_file = '/proc/net/tcp';
    if (file_exists($tcp_file)) {
        $connections = count(file($tcp_file)) - 1; // Subtract header line
    }
} catch (Exception $e) {
    $connections = 0;
}

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