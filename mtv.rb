#!/usr/local/Cellar/ruby/3.0.2/bin/ruby

require 'fileutils'

if Dir.entries('.').grep(/mtv$/).include?("mtv") == true
        puts "\nI found an existing mtv directory, entering it\n\n"
        FileUtils.cd('mtv')
else
        puts "I did not find an existing mtv directory, creating one and entering it\n\n"
        FileUtils.mkdir('mtv')
        FileUtils.cd('mtv')
end

puts "Completed files will be stored in #{FileUtils.pwd()}\n\n"

puts "Please enter your mtv.com url(s), separated by spaces:"
mtv_url = gets.chomp
mtv_list = mtv_url.split(" ")

mtv_list.each do |url|
system "youtube-dl #{url}"

mtv_act_listing = Dir.each_child('.').grep(/\.mp4$/).sort_by! { |c| File.mtime(c) }
mtv_act_length = mtv_act_listing.length

intermediate_file = 1
ts_list = []
concat = ""

for i in 1 .. mtv_act_length.to_i
unless i == mtv_act_length.to_i
        ts_list << i.to_s + ".ts|"
else
        ts_list << i.to_s + ".ts"
end
end

ts_list.each do |transport_stream|
        concat << transport_stream
end

episode_name = mtv_act_listing[0].split("_Act")

mtv_act_listing.each do |mp4|
        system "ffmpeg -i \"#{mp4}\" -c copy -bsf:v h264_mp4toannexb -f mpegts \"#{intermediate_file}.ts\""
        intermediate_file += 1
end

system "ffmpeg -i \"concat:#{concat}\" -c copy -bsf:a aac_adtstoasc -movflags faststart \"#{episode_name[0]}.mov\""

FileUtils.rm Dir.glob('*.mp4')
FileUtils.rm Dir.glob('*.ts')
end