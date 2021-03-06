export interface IEmotions {
    angry: number;
    joy: number;
    suprise: number;
    sorrow: number;
}

export interface ImageFrame {
    image: string;
    emotions: IEmotions;
    text: string;
}
