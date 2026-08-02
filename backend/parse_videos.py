"""批量解析真实抖音视频链接 - 增强版"""
import sys
import asyncio
import json

sys.path.insert(0, 'D:/桌面/douyin-collector/backend')

from parser import parse_douyin_url, extract_url, resolve_video_id

VIDEOS = [
    {
        "share_text": "3.56 复制打开抖音，看看【🇨 🇯  🇭的作品】高中生比完国赛后采访答辩评委！ 刚刚比完 全国学生... https://v.douyin.com/weonBsiFHOw/ :2pm Rxs:/ g@b.nq 12/06",
        "video_id": "weonBsiFHOw"
    },
    {
        "share_text": "7.99 复制打开抖音，看看【胡楚靓的作品】如何用AI做自己的专属工作台，别太简单 # AI ... https://v.douyin.com/uWYClsfxMHg/ a@N.WM Kjp:/ 04/28 :3pm",
        "video_id": "uWYClsfxMHg"
    },
    {
        "share_text": "1.58 复制打开抖音，看看【AI乐未来的作品】秒秒guo的vibe coding的音乐播放器产品... https://v.douyin.com/s2qCXmZPkcg/ :4pm 07/25 fbN:/ M@J.II",
        "video_id": "s2qCXmZPkcg"
    },
    {
        "share_text": "5.64 复制打开抖音，看看【大娱乐家的作品】前辈们，是你们回来看我们了吗# 八一建军节 # 江... https://v.douyin.com/basDnfn_r6o/ :4pm wSY:/ 11/01 R@x.SY",
        "video_id": "basDnfn_r6o"
    },
    {
        "share_text": "2.58 复制打开抖音，看看【合一说AI效能的作品】# ai从业者 # Workbuddy # OPC... https://v.douyin.com/EuYo3S4dAKs/ :7pm 12/09 l@C.Uy mQx:/",
        "video_id": "EuYo3S4dAKs"
    },
]

async def main():
    results = []
    for i, v in enumerate(VIDEOS):
        print(f"\n{'='*60}")
        print(f"解析视频 {i+1}/{len(VIDEOS)}...")
        try:
            info = await parse_douyin_url(v["share_text"])
            if info:
                print(f"  标题: {info.get('title', 'N/A')[:50]}")
                print(f"  作者: {info.get('author', 'N/A')}")
                print(f"  点赞: {info.get('like_count', 0)}")
                print(f"  描述: {info.get('description', 'N/A')[:80]}...")
                print(f"  视频ID: {info.get('source_url', 'N/A')}")
                results.append({"success": True, "data": info})
            else:
                print("  解析失败: 无返回数据")
                results.append({"success": False, "error": "no_data"})
        except Exception as e:
            print(f"  解析失败: {e}")
            results.append({"success": False, "error": str(e)})
    
    # 保存结果
    output_path = 'D:/桌面/douyin-collector/backend/parsed_videos_v2.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"解析完成，结果已保存到 {output_path}")
    success_count = sum(1 for r in results if r["success"])
    print(f"成功: {success_count}/{len(results)}")
    
    # 打印详细信息
    for i, r in enumerate(results):
        print(f"\n视频 {i+1}:")
        if r["success"]:
            d = r["data"]
            print(f"  标题: {d.get('title', 'N/A')}")
            print(f"  作者: {d.get('author', 'N/A')}")
            print(f"  点赞: {d.get('like_count', 0)}")
            print(f"  评论: {d.get('comment_count', 0)}")
            print(f"  分享: {d.get('share_count', 0)}")
            print(f"  标签: {d.get('tags', [])}")
        else:
            print(f"  失败: {r['error']}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
