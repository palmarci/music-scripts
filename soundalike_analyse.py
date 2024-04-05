import re
import argparse

def parse_info(info):
    # Extracting information using regular expressions
    match = re.search(r'^(.*?) - (.*?)\.(\w+)\s+(\d+\.\d+) MB\s+(\d+\.\d+) sec$', info)
    if match:
        return match.group(1), match.group(2), match.group(3), float(match.group(4)), float(match.group(5))
    else:
        return None

def analyze_groups(groups, percentage):
    for group_index, group in enumerate(groups):
        files_info = [parse_info(info) for info in group.split('\n') if info.strip()]

        # Check if any parsing failed
        if any(file_info is None for file_info in files_info):
            print(f"Error parsing group {group_index + 1}. Skipping.")
            continue
        
        for i in range(len(files_info)):
            for j in range(i+1, len(files_info)):
                # Comparing file sizes and durations within +/-percentage%
                size_ratio = max(files_info[i][3], files_info[j][3]) / min(files_info[i][3], files_info[j][3])
                duration_ratio = max(files_info[i][4], files_info[j][4]) / min(files_info[i][4], files_info[j][4])
                
                if (1 - percentage/100) <= size_ratio <= (1 + percentage/100) and \
                   (1 - percentage/100) <= duration_ratio <= (1 + percentage/100):
                    print(f"Match found in group {group_index + 1}:\n"
                          f"{files_info[i][0]} - {files_info[i][1]}.{files_info[i][2]}\n"
                          f"{files_info[j][0]} - {files_info[j][1]}.{files_info[j][2]}\n"
                          f"Size Ratio: {size_ratio:.4f}, Duration Ratio: {duration_ratio:.4f}\n")

def main():
    parser = argparse.ArgumentParser(description='Analyze and compare file information.')
    parser.add_argument('input_file', help='Path to the output file of soundalike')
    parser.add_argument('--percentage', type=float, default=5, help='Percentage for comparison (default: 5)')

    args = parser.parse_args()

    with open(args.input_file, 'r') as file:
        input_text = file.read()

    # Splitting input into groups using two consecutive newlines
    groups = input_text.strip().split('\n\n')
    
    # Analyzing and printing matching groups
    analyze_groups(groups, args.percentage)

if __name__ == "__main__":
    main()
