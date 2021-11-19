#!/usr/local/bin/ruby
require 'fileutils'

if Dir.entries('.').grep(/^mtv-dl$/).include?("mtv-dl")
        puts "\nI found an existing mtv-dl directory, entering it\n\n"
        FileUtils.cd('mtv-dl')
else
        puts "I did not find an existing mtv-dl directory, creating one and entering it\n\n"
        FileUtils.mkdir('mtv-dl')
        FileUtils.cd('mtv-dl')
end

puts "Completed files will be stored in #{FileUtils.pwd()}\n\n"
puts "Please enter your mtv.com url(s), separated by spaces:"

mtv_url = gets.strip
mtv_list = mtv_url.split(" ")

mtv_list.each do |url|
        system "yt-dlp #{url}"
        mtv_act_listing = Dir.each_child('.').grep(/\.mp4$/).sort_by! { |c| File.mtime(c) }
        intermediate_file = 1
        ts_file = []
        ts_list = ""
        for i in 1 .. mtv_act_listing.length
                unless i == mtv_act_listing.length
                        ts_file.push(i.to_s + ".ts|")
                else
                        ts_file.push(i.to_s + ".ts")
                end
        end
        ts_file.each do |ts_file_name|
                ts_list.concat ts_file_name
        end
        episode_name = mtv_act_listing[0].split("_Act")
        mtv_act_listing.each do |mp4|
                system "ffmpeg -i \"#{mp4}\" -c copy -bsf:v h264_mp4toannexb -f mpegts \"#{intermediate_file}.ts\""
                intermediate_file += 1
        end
        system "ffmpeg -i \"concat:#{ts_list}\" -c copy -bsf:a aac_adtstoasc -movflags faststart \"#{episode_name[0]}.mov\""
        FileUtils.rm Dir.glob('*.mp4')
        FileUtils.rm Dir.glob('*.ts')
end
